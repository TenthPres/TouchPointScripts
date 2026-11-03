# Atrium Control

Integration between TouchPoint and a CDVI Atrium access control system, built on Atrium's official SDK
(`POST /sdk.xml`).  How the protocol works is in [API-NOTES.md](API-NOTES.md).

| Script | What it does |
| --- | --- |
| `AtriumLib.py` | Shared client.  Not run directly; the others load it. |
| `AtriumSync.py` | Creates/updates Atrium users for people matching TouchPoint searches and sets their access levels. |
| `AtriumScheduleSync.py` | Writes Atrium schedules from room reservations, or from custom SQL. |
| `AtriumControl.py` | Wireless lock battery report; code-callable momentary unlock and lockdown start/stop. |

## Setup
1. In Atrium, create an operator account for this integration with **SDK login** enabled, and give it only the rights
   it needs.  (Atrium sessions last 15 minutes; the client logs in again by itself.)
2. In TouchPoint Settings, add `AtriumApiUrl`, `AtriumApiUser`, `AtriumApiPassword`.
3. Create the Special Content text file `AtriumConfig.json` (below).  **`dryRun` defaults to true**: scripts print what
   they would do and change nothing until you set it false.

```json
{
  "dryRun": true,
  "changeLimit": 25,
  "guidExtraValue": "AtriumGuid",
  "linkByName": false,
  "syncNames": true,
  "disableWhenNoAccess": true,
  "rules": [
    {"name": "Staff", "accessLevel": "Staff", "search": "StatusFlag = 'F10'"},
    {"name": "Children's volunteers", "accessLevel": "ChildrenYouth", "search": "StatusFlag = 'F11'"}
  ],
  "schedules": {
    "cycleDays": 7,
    "horizonHours": 4,
    "mappings": [
      {"scheduleId": 30, "reservableId": 123, "minutesBefore": 15, "minutesAfter": 15},
      {"scheduleId": 24, "restrictedAreaReservableId": 27, "minutesBefore": 15, "minutesAfter": 15},
      {"scheduleId": 31, "sql": "SELECT StartAt AS WindowStart, EndAt AS WindowEnd FROM ..."}
    ]
  },
  "doors": {"Front Doors": {"serial": "00009F90", "id": 0}}
}
```

## Schedule mappings
- `reservableId`: the door is open whenever that reservable is reserved (the "Access: Door 01 Code" style reservables).
- `restrictedAreaReservableId`: the door is open during ordinary events in that area or any space beneath it, and
  locked while a children's event (a meeting of an involvement whose Involvement Type code is `CHILD`) is in the area.
  Padding (`minutesBefore`/`minutesAfter`) widens ordinary events only.
  - The lock begins `childBufferMinutes` (default 20) before the children's event and ends that long after it, or
    covers the reservation's setup/teardown time if that is longer.
  - `defaultIsLocked` (boolean, default `true`) sets what happens when nothing is reserved; `false` keeps
    the space open except around children's events.
- Cancelled meetings (`DidNotMeet`) and denied reservations are ignored.  An ordinary event opens a door only once
  approved (or if it never needed approval); a pending children's event already locks it.
- `sql`: your own query returning `WindowStart` and `WindowEnd`.

## Safety properties
- **Only linked users are touched.**  The link is the Atrium user's GUID, stored on the person as a text Extra Value
  (`AtriumGuid` by default, `guidExtraValue` to rename).  The GUID is used rather than Atrium's numeric id because ids can
  be reused after a delete.  A missing or dangling GUID is reported and the person treated as unlinked; two people
  claiming one GUID are both left alone; Atrium users it didn't create or link are never touched.
- **Access levels outside your rules are preserved** on linked users.
- **Nothing is deleted.**  People who stop qualifying lose the levels your rules manage and (optionally) are disabled.
- **An empty result is treated as a broken search**, not as "revoke everyone", unless `allowEmptyRun` is set.
- **A same-named, unlinked Atrium user is never duplicated.**  It is reported; set `linkByName` to adopt it when the
  match is unique.
- **Change limits.**  A run that would exceed `changeLimit` writes applies nothing and says so.
- **Built-in and protected schedules (ids 0-5, read-only) are never modified.**
- **Dangerous commands need `confirm=True`** in code and `AtriumConfirm = "YES"` from a script; unlock time is capped at
  300 seconds.

## Things to know
- Atrium holds **5 access levels per user** and **100 periods per schedule**.  Overflows are reported, not silently cut.
- **Schedule sync runs in two modes.**  *Full* (daily, MorningBatch) rewrites each schedule's cycle from today's midnight.
  *Near* (hourly, ScheduledTasks) re-reads only the next `horizonHours` (default 4) and swaps just that slice into the
  existing cycle; it never moves the cycle and defers to the next full run if the cycle is missing or stale.  Near mode
  throttles itself to about once an hour, whatever ScheduledTasks' frequency.  An Atrium schedule is a repeating cycle,
  so if the daily run stops, the last cycle repeats.
- **Atrium users have no email or ID field** on the controller, which is why the GUID Extra Value is the link.  Anything
  the desktop software stores beyond the controller's record is not reachable through this API.
- **Installing:** build with `gulp`, upload `AtriumControl.zip`.  `Install.py` adds the daily calls to MorningBatch and the
  near-term call to ScheduledTasks; everything stays a dry run until `dryRun` is false.
- **Status of the code.**  Unit tests: `python -m unittest discover tests` (from this folder).  Verified against the live
  controller: all reads; a reversible user rename and access-level change; schedule full write and near-mode slice swap
  (on a spare schedule, restored exactly); a 5-second door unlock (on a physically disabled door); wireless lock battery
  reads.  **Not yet verified:** creating/deleting a user, lockdown (deliberately untested), and running inside
  TouchPoint's IronPython, including `model.AddExtraValueText` and `PeopleExtra` reads.

## Future work (not built)
See [DESIGN-FUTURE.md](DESIGN-FUTURE.md): importing card scans into TouchPoint, and managing cards from TouchPoint.
