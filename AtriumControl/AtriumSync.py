# Pckgd
# Title: Atrium Sync
# Description: Keep Atrium users and their access levels in line with TouchPoint searches and status flags.
# Updates from: GitHub/TenthPres/TouchPointScripts/AtriumControl/AtriumSync.py
# Depends on: AtriumLib.py
# Version: 0.2.7
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

# Configuration lives in Special Content as AtriumConfig.json.  Each linked person carries their Atrium user's GUID in a
# text Extra Value (default name "AtriumGuid"), which is the only link between the two systems.  See README.md.
#
# Rules of engagement, because this changes who can open doors:
#  - It only ever touches Atrium users linked through the Extra Value.  Everyone else in Atrium is left alone.
#  - Access levels that no rule mentions are left alone on linked users.
#  - It never deletes anything.  People who stop qualifying lose their managed levels and are optionally disabled.
#  - Nothing is written unless "dryRun" is false and "peopleDryRun" is explicitly false, and no run may make more than
#    "changeLimit" changes.  ("dryRun" is shared with AtriumScheduleSync; "peopleDryRun" gates only this script.)

global model, Data, q

import datetime
import json
import re

try:
    exec(model.PythonContent("AtriumLib").replace("\r\n", "\n").replace("\r", "\n"), globals())
except NameError:  # running under test, where AtriumLib is imported normally
    from AtriumLib import *  # noqa

DEFAULT_CONFIG = {
    "dryRun": True,
    "peopleDryRun": True,  # this script stays a dry run until this is the literal false, even once "dryRun" is false
    "changeLimit": 25,
    "timeBudgetSeconds": 60,  # reading from Atrium stops with an error past this, before a web gateway gives up; 0 = none
    "guidExtraValue": "AtriumGuid",
    "linkByName": True,  # adopt an existing, unlinked Atrium user when exactly one has the same first and last name
    "createUsers": False,  # a person nobody in Atrium matches is reported, not created, until this is true
    "syncNames": True,
    "disableWhenNoAccess": True,
    "allowEmptyRun": False,  # a run where nobody qualifies is almost always a broken search, so refuse unless allowed
    "rules": [],  # [{"name": "Staff", "accessLevel": "Staff", "search": "StatusFlag = 'F10'"}]
}


# ---------------------------------------------------------------------------------------------------------------------
# Planning (pure; no TouchPoint or network calls)
# ---------------------------------------------------------------------------------------------------------------------

def name_key(first, last):
    return (ascii_name(first).lower(), ascii_name(last).lower())


def _plain(value):
    return ascii_name(value).lower()


def describe_person(pid, want):
    """A person as the warnings name them: enough to find them in TouchPoint, including a nickname that differs."""
    name = "{} {}".format(want["first"], want["last"]).strip()
    if want.get("nick") and _plain(want["nick"]) != _plain(want["first"]):
        name += ", goes by {}".format(want["nick"])
    return "Person {} ({})".format(pid, name)


def describe_user(u):
    """An Atrium user as the warnings name them: their name in Atrium and the GUID that makes the link."""
    return '{} (GUID {})'.format(u["name"], u["guid"])


def html_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unlinked_users_table(users):
    """An HTML table of Atrium users (name and GUID), for finding the right one to link a person to by hand."""
    rows = "".join("<tr><td>{}</td><td><code>{}</code></td></tr>".format(html_escape(u["name"]), html_escape(u["guid"]))
                   for u in users)
    return ("<p>Atrium users nobody is linked to ({}), for linking by hand:</p>"
            "<table class='table table-striped table-condensed'><thead><tr><th>Atrium user</th><th>GUID</th></tr></thead>"
            "<tbody>{}</tbody></table>".format(len(users), rows))


def plan_sync(qualified, users, links, managed_levels, options, empty_levels=(), report=None):
    """
    qualified:      {peopleId(int): {"first": str (formal), "last": str, "nick": str (optional), "levels": [...]}}
    users:          list of parse_user() dicts from Atrium
    links:          {peopleId(int): guid} as read from the Extra Value
    managed_levels: set of access level ids that rules control
    empty_levels:   access level ids whose rule matched nobody (a renamed saved search looks just like that)
    report:         optional dict; if someone is left unmatched, report["unlinked_users"] gets the Atrium users nobody
                    is linked to, sorted by surname then first name
    returns (actions, warnings)

    Actions are dicts with a "kind" of: create, link, update.  "update" carries only the changed fields.  The GUID,
    not the numeric Atrium id, is the link, because ids can be reused after a delete.
    """
    actions, warnings = [], []
    by_guid = dict((u["guid"], u) for u in users)

    holders = {}
    for pid, guid in links.items():
        holders.setdefault(guid, []).append(pid)
    blocked = set()
    for guid, pids in holders.items():
        if len(pids) > 1:
            warnings.append("People {} all claim the same Atrium user; leaving all of them alone until fixed."
                            .format(sorted(pids)))
            blocked.update(pids)

    live_links = {}
    for pid, guid in links.items():
        if pid in blocked:
            continue
        u = by_guid.get(guid)
        if u is None:
            warnings.append("Person {} has an Atrium GUID that no longer exists; treating them as unlinked.".format(pid))
            continue
        live_links[pid] = u
    claimed = set(g for g in holders if g in by_guid)  # an Atrium user someone claims is never adopted by name

    if not qualified and live_links and not options.get("allowEmptyRun"):
        warnings.append("Nobody qualifies for any rule but {} people are linked.  Refusing to revoke everything; "
                        "check the searches (or set allowEmptyRun).".format(len(live_links)))
        return actions, warnings

    # One rule going quiet is as suspicious as all of them: a saved search that was renamed or deleted matches nobody,
    # and that would read as "everyone holding its level no longer qualifies".
    holding_empty = [pid for pid, u in live_links.items() if set(u["access_levels"]) & set(empty_levels)]
    if holding_empty and not options.get("allowEmptyRun"):
        warnings.append("A rule matched nobody, but {} linked people hold the access level it manages.  Refusing to "
                        "revoke them; check that rule's search (or set allowEmptyRun).".format(len(holding_empty)))
        return actions, warnings

    unlinked_by_name = {}
    adopted = set()  # GUIDs of Atrium users this plan has already linked to someone
    unmatched = 0  # people left alone because nobody in Atrium matched and creating users is off
    ev = options.get("guidExtraValue", "AtriumGuid")
    for u in users:
        if u["guid"] not in claimed:
            unlinked_by_name.setdefault(name_key(u["first_name"], u["last_name"]), []).append(u)

    for pid in sorted(qualified):
        if pid in blocked:
            continue
        want = qualified[pid]
        u = live_links.get(pid)

        if u is None:
            # Atrium uses people's formal first names, so match on that first.  Only if nobody has it, try their
            # nickname: better to find an existing user under a nickname than to create a duplicate.
            match_key = name_key(want["first"], want["last"])
            candidates = unlinked_by_name.get(match_key, [])
            if not candidates and want.get("nick"):
                nick_key = name_key(want["nick"], want["last"])
                if unlinked_by_name.get(nick_key):
                    match_key, candidates = nick_key, unlinked_by_name[nick_key]
            by_hand = "To link by hand, put the right user's GUID in the {} Extra Value on person {}.".format(ev, pid)
            if candidates and not options.get("linkByName"):
                warnings.append("{} has the same name as an existing, unlinked Atrium user: {}.  Not creating a "
                                "duplicate; turn on linkByName to adopt them.  {}".format(
                                    describe_person(pid, want), "; ".join(describe_user(c) for c in candidates), by_hand))
                continue
            if len(candidates) > 1:
                warnings.append("{} matches {} unlinked Atrium users by name, so none was chosen: {}.  {}".format(
                    describe_person(pid, want), len(candidates), "; ".join(describe_user(c) for c in candidates), by_hand))
                continue
            if len(candidates) == 1:
                u = candidates[0]
                unlinked_by_name[match_key] = []
                adopted.add(u["guid"])
                actions.append({"kind": "link", "peopleId": pid, "guid": u["guid"]})
            else:
                if not options.get("createUsers"):
                    unmatched += 1
                    warnings.append("{} has no matching Atrium user, and creating users is turned off (createUsers).  "
                                    "{}  The Atrium users nobody is linked to are in the table below.".format(
                                        describe_person(pid, want), by_hand))
                    continue
                levels = _unique(want["levels"])
                if len(levels) > ACCESS_LEVEL_SLOTS:
                    warnings.append("Person {} qualifies for {} access levels; Atrium holds {}.  Truncated."
                                    .format(pid, len(levels), ACCESS_LEVEL_SLOTS))
                    levels = levels[:ACCESS_LEVEL_SLOTS]
                actions.append({"kind": "create", "peopleId": pid, "first": ascii_name(want["first"]),
                                "last": ascii_name(want["last"]), "levels": levels})
                continue

        changes = {}
        keep = [l for l in u["access_levels"] if l not in managed_levels]
        new_levels = keep + [l for l in _unique(want["levels"]) if l not in keep]
        if len(new_levels) > ACCESS_LEVEL_SLOTS:
            warnings.append("Person {} would need {} access levels; Atrium holds {}.  Truncated."
                            .format(pid, len(new_levels), ACCESS_LEVEL_SLOTS))
            new_levels = new_levels[:ACCESS_LEVEL_SLOTS]
        if sorted(new_levels) != sorted(u["access_levels"]):
            changes["access_levels"] = new_levels
        if options.get("syncNames") and name_key(u["first_name"], u["last_name"]) != name_key(want["first"], want["last"]):
            changes["first_name"] = ascii_name(want["first"])
            changes["last_name"] = ascii_name(want["last"])
        if not u["enabled"]:
            changes["enabled"] = True
        if changes:
            actions.append({"kind": "update", "peopleId": pid, "userId": u["id"], "changes": changes})

    for pid, u in sorted(live_links.items()):
        if pid in qualified:
            continue
        keep = [l for l in u["access_levels"] if l not in managed_levels]
        changes = {}
        if keep != u["access_levels"]:
            changes["access_levels"] = keep
        if options.get("disableWhenNoAccess") and not keep and u["enabled"]:
            changes["enabled"] = False
        if changes:
            actions.append({"kind": "update", "peopleId": pid, "userId": u["id"], "changes": changes})

    if unmatched and report is not None:
        # Once, not once per person: the Atrium users nobody is linked to, so the right one can be picked by name.
        report["unlinked_users"] = sorted((u for u in users if u["guid"] not in claimed and u["guid"] not in adopted),
                                          key=lambda u: (_plain(u["last_name"]), _plain(u["first_name"])))

    return actions, warnings


def _unique(items):
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def apply_actions(client, actions, set_link):
    """
    Executes the plan.  `set_link(peopleId, guid)` records the link (the Extra Value).  A created user's link is
    recorded immediately, so a later failure can't leave an orphan that the next run would duplicate.
    Returns a list of (action, error-or-None).
    """
    results = []
    for a in actions:
        try:
            if a["kind"] == "link":
                set_link(a["peopleId"], a["guid"])
            elif a["kind"] == "create":
                new_id = client.add_user(a["first"], a["last"], access_levels=a["levels"])
                set_link(a["peopleId"], client.get_user(new_id)["guid"])
            elif a["kind"] == "update":
                client.update_user(a["userId"], **a["changes"])
            results.append((a, None))
        except Exception as e:  # keep going; one bad record shouldn't strand the rest
            results.append((a, str(e)))
    return results


def count_writes(actions):
    return len([a for a in actions if a["kind"] in ("create", "update")])


# ---------------------------------------------------------------------------------------------------------------------
# TouchPoint glue
# ---------------------------------------------------------------------------------------------------------------------

def load_json(name, default):
    raw = model.TextContent(name)
    return json.loads(raw) if raw else default


def resolve_level(spec, levels_by_label):
    if isinstance(spec, int) or str(spec).isdigit():
        return int(spec)
    found = levels_by_label.get(str(spec).strip().lower())
    if found is None:
        raise AtriumError("No Atrium access level named '{}'".format(spec))
    return found


def people_names(pids):
    names = {}
    pids = list(pids)
    for i in range(0, len(pids), 400):
        chunk = pids[i:i + 400]
        for r in q.QuerySql(
                "SELECT PeopleId, FirstName AS First, NickName AS Nick, LastName AS Last "
                "FROM People WHERE PeopleId IN ({})".format(",".join(str(int(p)) for p in chunk))):
            names[int(r.PeopleId)] = (r.First or "", r.Last or "", r.Nick or "")
    return names


class PhaseTimer(object):
    """Records how long each phase of a run took and how many Atrium requests it made, to show where a slow run went."""

    def __init__(self, client, clock=datetime.datetime.now):
        self.client, self.clock = client, clock
        self.start = self.last = clock()
        self.last_requests = client.request_count
        self.phases = []

    def mark(self, label):
        now, count = self.clock(), self.client.request_count
        self.phases.append((label, (now - self.last).total_seconds(), count - self.last_requests))
        self.last, self.last_requests = now, count

    def summary(self):
        parts = ["{} {:.1f}s ({} requests)".format(label, secs, n) for label, secs, n in self.phases]
        return "{}.  Total {:.1f}s.".format("; ".join(parts), (self.last - self.start).total_seconds())


def rules_need_level_names(rules):
    """Looking up access level names means reading the controller's whole level table; numeric ids don't need it."""
    return any(not (isinstance(r["accessLevel"], int) or str(r["accessLevel"]).isdigit()) for r in rules)


def is_dry_run(config):
    """True unless both the shared dryRun and this script's own peopleDryRun have been turned off on purpose."""
    return bool(config["dryRun"]) or config["peopleDryRun"] is not False


def search_people_ids(search):
    """
    Every PeopleId a TouchPoint search matches.  q.QueryList stops at 1000 people unless told otherwise, and a short
    list here would read as "these people no longer qualify" and strip their access, so ask for the whole count and
    refuse to go on if what comes back doesn't add up.
    """
    total = int(q.QueryCount(search))
    ids = set(int(p.PeopleId) for p in q.QueryList(search, "name", max(total, 1), 0))
    if len(ids) != total:
        raise AtriumError("Search {!r} matches {} people but only {} were returned; not syncing from a partial "
                          "list.".format(search, total, len(ids)))
    return ids


def rule_search(rule):
    """
    What to hand TouchPoint's search for a rule.  A rule gives either "search" (search code, or a saved search's name)
    or "queryId" (a saved search's id).  The id is looked up to its current name each run, so the saved search can be
    renamed and edited in TouchPoint without touching this config; the definition itself always lives in TouchPoint.
    """
    query_id = rule.get("queryId")
    if not query_id:
        if not rule.get("search"):
            raise AtriumError("Rule {!r} needs a \"search\" or a \"queryId\".".format(rule.get("name")))
        return rule["search"]
    query_id = str(query_id).strip().lower()
    if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", query_id):
        raise AtriumError("Rule {!r}: '{}' is not a saved search id.".format(rule.get("name"), query_id))
    rows = list(q.QuerySql("SELECT name AS QueryName FROM Query WHERE QueryId = '{}'".format(query_id)))
    if not rows:
        raise AtriumError("Rule {!r}: no saved search has the id {}.".format(rule.get("name"), query_id))
    name = rows[0].QueryName
    # TouchPoint finds a saved search by name, so a name two searches share could run the wrong one.
    sharing = int(list(q.QuerySql("SELECT COUNT(*) AS N FROM Query WHERE name = '{}'".format(name.replace("'", "''"))))[0].N)
    if sharing != 1:
        raise AtriumError("Rule {!r}: {} saved searches are named {!r}; rename them so each name is unique."
                          .format(rule.get("name"), sharing, name))
    return name


def run():
    config = dict(DEFAULT_CONFIG)
    config.update(load_json("AtriumConfig.json", {}))
    ev = config["guidExtraValue"]

    client = AtriumClient(model.Setting("AtriumApiUrl", ""), model.Setting("AtriumApiUser", ""),
                          model.Setting("AtriumApiPassword", ""), touchpoint_transport(model))
    client.set_time_budget(config["timeBudgetSeconds"])
    timer = PhaseTimer(client)
    levels_by_label = {}
    if rules_need_level_names(config["rules"]):
        levels_by_label = dict((l["label"].strip().lower(), l["id"]) for l in client.list_access_levels())
    timer.mark("access levels")

    qualified, managed, empty_levels = {}, set(), set()
    for rule in config["rules"]:
        level = resolve_level(rule["accessLevel"], levels_by_label)
        managed.add(level)
        matched = search_people_ids(rule_search(rule))
        if not matched:
            empty_levels.add(level)
        for pid in matched:
            entry = qualified.setdefault(pid, {"levels": []})
            entry["levels"].append(level)
    names = people_names(qualified.keys())
    for pid in list(qualified):
        if pid not in names:
            del qualified[pid]
            continue
        qualified[pid]["first"], qualified[pid]["last"], qualified[pid]["nick"] = names[pid]

    links = dict((int(r.PeopleId), r.Data) for r in q.QuerySql(
        "SELECT PeopleId, Data FROM PeopleExtra WHERE Field = '{}' AND Data IS NOT NULL AND Data <> ''"
        .format(ev.replace("'", "''"))))
    timer.mark("TouchPoint searches and links")

    users = client.list_users()
    timer.mark("Atrium users ({})".format(len(users)))
    report = {}
    actions, warnings = plan_sync(qualified, users, links, managed, config, empty_levels, report)
    writes = count_writes(actions)

    dry = is_dry_run(config)
    print("<h3>Atrium Sync{}</h3>".format(" (dry run)" if dry else ""))
    print("<p>Timing: {}</p>".format(timer.summary()))
    for w in warnings:
        print("<p><b>Warning:</b> {}</p>".format(html_escape(w)))
    print("<p>{} qualifying people, {} planned actions ({} Atrium writes).</p>".format(len(qualified), len(actions), writes))
    for a in actions:
        print("<div>{}</div>".format(json.dumps(a)))
    if "unlinked_users" in report:
        print(unlinked_users_table(report["unlinked_users"]))

    if dry:
        return
    if writes > config["changeLimit"]:
        print("<p><b>Not applied:</b> {} writes exceeds changeLimit of {}.  Review the plan, then raise the limit or "
              "run again after correcting the cause.</p>".format(writes, config["changeLimit"]))
        return

    client.set_time_budget(None)  # the budget is for reading; stopping halfway through a write could orphan a new user

    def set_link(pid, guid):
        model.AddExtraValueText(pid, ev, guid)

    for a, err in apply_actions(client, actions, set_link):
        if err:
            print("<p><b>Failed:</b> {} &mdash; {}</p>".format(json.dumps(a), err))


if "model" in globals() and hasattr(model, "TextContent"):
    run()
