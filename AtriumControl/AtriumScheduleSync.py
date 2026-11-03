# Pckgd
# Title: Atrium Schedule Sync
# Description: Open Atrium doors on schedules driven by TouchPoint room reservations or custom SQL.
# Updates from: GitHub/TenthPres/TouchPointScripts/AtriumControl/AtriumScheduleSync.py
# Depends on: AtriumLib.py
# Version: 0.2.0
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

# Each mapping in AtriumConfig.json -> "schedules" -> "mappings" ties one Atrium schedule to either a TouchPoint
# reservable ("reservableId") or your own SQL ("sql") that returns WindowStart and WindowEnd columns.  Custom SQL may use
# the tokens {start} and {end} (yyyy-MM-dd HH:mm:ss) for the period being synced, to avoid reading more than it needs.
#
#   {"cycleDays": 7, "horizonHours": 4, "mappings": [
#       {"scheduleId": 30, "reservableId": 123, "minutesBefore": 15, "minutesAfter": 15},
#       {"scheduleId": 31, "sql": "SELECT StartAt AS WindowStart, EndAt AS WindowEnd FROM ... WHERE EndAt > '{start}' AND StartAt < '{end}'"}]}
#
# Two modes, chosen by Data.AtriumScheduleMode before the script is called:
#   "full" (default, run daily): rewrites each schedule's whole cycle starting at today's midnight.
#   "near" (run hourly):         re-reads only the next `horizonHours` (default 4) and replaces just that slice, leaving
#                                the rest of the cycle exactly as the last full run wrote it.  It never moves the cycle,
#                                and it asks for a full run instead if the cycle is missing or out of date.
#
# An Atrium schedule is a repeating cycle, so if the daily run stops, the last cycle keeps repeating.  Built-in schedules
# (ids 0-5) and read-only schedules are never modified.

global model, Data, q

import datetime
import json

try:
    exec(model.PythonContent("AtriumLib"), globals())
except NameError:  # running under test
    from AtriumLib import *  # noqa

DEFAULT_RESERVATION_SQL = """
    SELECT MIN(DATEADD(MINUTE, -{before}, r.ReservationStart)) AS WindowStart,
           MAX(DATEADD(MINUTE, {after}, r.ReservationEnd)) AS WindowEnd
    FROM Reservations r
        JOIN Meetings m ON r.MeetingId = m.MeetingId
    WHERE r.ReservableId = {rid}
      AND m.Canceled = 0
      AND DATEADD(MINUTE, {after}, r.ReservationEnd) > '{start}'
      AND DATEADD(MINUTE, -{before}, r.ReservationStart) < '{end}'
    GROUP BY r.MeetingId
"""

NEAR_RUN_GAP = datetime.timedelta(minutes=50)  # the hourly job may be triggered more often than hourly; run once per hour
FMT = "%Y-%m-%d %H:%M:%S"


def to_datetime(value):
    """Accepts a Python datetime or a .NET DateTime from a TouchPoint query."""
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime(value.Year, value.Month, value.Day, value.Hour, value.Minute, value.Second)


def expand_current(schedule, range_start, range_end):
    """Where an existing (repeating) schedule is open between two datetimes, as (start, end) datetimes."""
    cycle = schedule["cycle_seconds"]
    out = []
    if cycle <= 0:
        return out
    delta = datetime.timedelta
    k = int((range_start - schedule["start"]).total_seconds() // cycle) - 1
    while schedule["start"] + delta(seconds=k * cycle) < range_end:
        base = schedule["start"] + delta(seconds=k * cycle)
        for a, b in schedule["periods"]:
            out.append((base + delta(seconds=a), base + delta(seconds=b)))
        k += 1
    return out


def _periods_to_windows(start, periods):
    return [(start + datetime.timedelta(seconds=a), start + datetime.timedelta(seconds=b)) for a, b in periods]


def replace_slice(existing, fresh, region_start, region_end):
    """
    `existing` and `fresh` are lists of (start, end) datetimes.  Returns existing with everything inside
    [region_start, region_end) removed, plus the part of `fresh` that falls inside the region.
    """
    kept = []
    for a, b in existing:
        if b <= region_start or a >= region_end:
            kept.append((a, b))
            continue
        if a < region_start:
            kept.append((a, region_start))
        if b > region_end:
            kept.append((region_end, b))
    for a, b in fresh:
        a, b = max(a, region_start), min(b, region_end)
        if b > a:
            kept.append((a, b))
    return kept


def _summary(schedule, wanted, have, start, cycle_days, windows):
    return {"scheduleId": schedule["id"], "label": schedule["label"], "windows": len(wanted),
            "add": len([w for w in wanted if w not in have]), "remove": len([w for w in have if w not in wanted]),
            "start": start, "cycleDays": cycle_days, "raw": windows}


def plan_schedule(schedule, windows, start, cycle_days):
    """
    Full mode.  Returns None if the schedule already does what we want over the coming cycle, otherwise a dict
    describing the write.  `schedule` is parse_schedule() output; `windows` are (datetime, datetime) pairs.
    """
    end = start + datetime.timedelta(days=cycle_days)
    wanted = normalize_windows(start, cycle_days, windows)
    have = normalize_windows(start, cycle_days, expand_current(schedule, start, end))
    if wanted == have and schedule["cycle_seconds"] == cycle_days * 86400:
        return None
    return _summary(schedule, wanted, have, start, cycle_days, windows)


def plan_schedule_near(schedule, fresh, now, horizon_hours, cycle_days):
    """
    Near mode.  Keeps the schedule's own cycle and swaps in fresh data for [now, now + horizon).  Returns
    (plan-or-None, reason-or-None); a reason means the cycle needs a full run first.
    """
    start = schedule["start"]
    end = start + datetime.timedelta(days=cycle_days)
    if schedule["cycle_seconds"] != cycle_days * 86400:
        return None, "its cycle length is not {} days".format(cycle_days)
    if not (start <= now < end):
        return None, "its cycle does not cover the current time (last full run is stale)"
    region_end = min(now + datetime.timedelta(hours=horizon_hours), end)
    existing = _periods_to_windows(start, schedule["periods"])
    desired = replace_slice(existing, fresh, now, region_end)
    wanted = normalize_windows(start, cycle_days, desired)
    have = normalize_windows(start, cycle_days, existing)
    if wanted == have:
        return None, None
    return _summary(schedule, wanted, have, start, cycle_days, desired), None


def fetch_windows(mapping, start, end):
    s, e = start.strftime(FMT), end.strftime(FMT)
    if mapping.get("sql"):
        sql = mapping["sql"].replace("{start}", s).replace("{end}", e)
    else:
        sql = DEFAULT_RESERVATION_SQL.format(rid=int(mapping["reservableId"]), before=int(mapping.get("minutesBefore", 0)),
                                             after=int(mapping.get("minutesAfter", 0)), start=s, end=e)
    return [(to_datetime(r.WindowStart), to_datetime(r.WindowEnd)) for r in q.QuerySql(sql)]


def run():
    config = json.loads(model.TextContent("AtriumConfig.json") or "{}")
    dry = config.get("dryRun", True)
    limit = config.get("changeLimit", 25)
    sched_cfg = config.get("schedules", {})
    cycle_days = int(sched_cfg.get("cycleDays", 7))
    horizon = int(sched_cfg.get("horizonHours", 4))
    mappings = sched_cfg.get("mappings", [])
    mode = (getattr(Data, "AtriumScheduleMode", None) or "full") if hasattr(Data, "AtriumScheduleMode") else "full"
    if mode not in ("full", "near"):
        raise AtriumError("AtriumScheduleMode must be 'full' or 'near'")

    seen = set()
    for m in mappings:
        if m["scheduleId"] in seen:
            raise AtriumError("Schedule {} is mapped twice".format(m["scheduleId"]))
        seen.add(m["scheduleId"])

    now = datetime.datetime.now()
    stamp_name = "AtriumScheduleNearLastRun.txt"
    if mode == "near" and not (hasattr(Data, "AtriumScheduleForce") and Data.AtriumScheduleForce):
        last = model.TextContent(stamp_name)
        if last:
            try:
                if now - datetime.datetime.strptime(last.strip(), FMT) < NEAR_RUN_GAP:
                    return
            except ValueError:
                pass

    client = AtriumClient(model.Setting("AtriumApiUrl", ""), model.Setting("AtriumApiUser", ""),
                          model.Setting("AtriumApiPassword", ""), touchpoint_transport(model))
    today = datetime.datetime(now.year, now.month, now.day)

    plans, notes = [], []
    for m in mappings:
        schedule = client.get_schedule(m["scheduleId"])
        if mode == "full":
            plan = plan_schedule(schedule, fetch_windows(m, today, today + datetime.timedelta(days=cycle_days)), today, cycle_days)
        else:
            plan, reason = plan_schedule_near(schedule, fetch_windows(m, now, now + datetime.timedelta(hours=horizon)),
                                              now, horizon, cycle_days)
            if reason:
                notes.append("Schedule {} skipped: {}.".format(m["scheduleId"], reason))
        if plan:
            plans.append(plan)

    print("<h3>Atrium Schedule Sync, {} mode{}</h3>".format(mode, " (dry run)" if dry else ""))
    for n in notes:
        print("<p><b>Note:</b> {}</p>".format(n))
    print("<p>{} of {} schedules need changes.</p>".format(len(plans), len(mappings)))
    for p in plans:
        print("<div>{} (#{}): +{} / -{} periods, {} total</div>".format(p["label"], p["scheduleId"], p["add"], p["remove"], p["windows"]))
    if dry:
        return
    if len(plans) > limit:
        print("<p><b>Not applied:</b> {} schedule writes exceeds changeLimit of {}.</p>".format(len(plans), limit))
        return
    for p in plans:
        try:
            client.set_schedule_windows(p["scheduleId"], p["start"], p["cycleDays"], p["raw"])
        except Exception as e:
            print("<p><b>Failed:</b> schedule {} &mdash; {}</p>".format(p["scheduleId"], e))
    if mode == "near":
        model.WriteContentText(stamp_name, now.strftime(FMT))


if "model" in globals() and hasattr(model, "TextContent"):
    run()
