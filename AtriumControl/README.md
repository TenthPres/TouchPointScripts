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
   they would do and change nothing until you set it false.  `dryRun` is shared by `AtriumScheduleSync` and
   `AtriumSync`, so the people sync has a second, separate gate: **`peopleDryRun` also defaults to true**, and
   `AtriumSync` only writes once `dryRun` is false *and* `peopleDryRun` is the literal `false`.  That lets the schedule
   sync run live while the people sync is still being proven.

```json
{
  "dryRun": true,
  "peopleDryRun": true,
  "timeBudgetSeconds": 60,
  "changeLimit": 25,
  "guidExtraValue": "AtriumGuid",
  "linkByName": true,
  "createUsers": false,
  "syncNames": true,
  "disableWhenNoAccess": true,
  "disableUsersWithOptions": false,
  "ignoreDisabledUsers": true,
  "rules": [
    {"name": "Staff", "accessLevel": "Staff", "search": "StatusFlag = 'F10'"},
    {"name": "Children's volunteers", "accessLevel": "ChildrenYouth", "queryId": "51e3c646-1661-4ee5-aa58-2dec4601f7d5"},
    {"name": "Common code", "accessLevel": "Common Code", "linkedEnabledUsers": true}
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
- **Users with option flags are never disabled** unless `disableUsersWithOptions` is true.  An Atrium user's option flags
  (`bit5` to `bit20` in the record) mark privileges beyond a card, such as being able to log in to Atrium, and disabling
  such a user would take that away.  Which flag is which isn't documented, so any flag set counts.  A user like that
  still loses the access levels the rules manage; they just stay enabled.
- **Disabled Atrium users are left alone** while `ignoreDisabledUsers` is true (the default): a linked user who is
  already disabled and no longer qualifies is not touched, and doesn't count towards the "nobody qualifies" checks.
  They are still synced if TouchPoint asks for them: a disabled user whose person qualifies is re-enabled and given the
  right levels, and a disabled user matched by name to a qualifying person is adopted the same way.  Set it to false to
  revoke managed levels from disabled users too.
- **An empty result is treated as a broken search**, not as "revoke everyone", unless `allowEmptyRun` is set.  That
  covers one rule going quiet as well as all of them: if a rule matches nobody while linked people still hold the
  access level it manages (say its saved search was renamed or deleted), nothing is revoked and the page says why.
- **Rules refer to searches, they don't copy them.**  A rule's `accessLevel` is a level name or numeric id.  Its group is
  `search` (search code, or a saved search's name) or `queryId` (a saved search's id, from its address in TouchPoint).
  The id is resolved to the saved search's current name on every run, so you can rename and edit the saved search in
  TouchPoint and the rule follows it.  Two saved searches sharing one name is an error when using `queryId`.
- **A rule can give its level to everyone known and enabled** instead of to a search's results, with
  `"linkedEnabledUsers": true` (and no `search`/`queryId`).  Every Atrium user linked to a TouchPoint person and enabled
  in Atrium then holds that level, on top of whatever their groups give them; unlinked users never get it.  It doesn't
  stop the sync disabling someone: a linked user in no group, with no other levels and no option flags, is still
  disabled, and loses that level with the rest.  A user who stays enabled for another reason (option flags, or levels
  outside your rules) keeps it.  Each of these is an Atrium write, so the first live run may need a larger `changeLimit`.
- **A same-named, unlinked Atrium user is never duplicated.**  `linkByName` (on by default) adopts it when the match is
  unique, trying the name Atrium should hold (see below) and then the other spelling; with it off the person is reported
  instead.
- **Atrium's first name is the person's TouchPoint nickname, or their first name if they have no nickname.**  That is
  the name given to a newly created user and, while `syncNames` is true (the default), the name a linked user is
  renamed to if it differs.  Set `syncNames` to false to leave existing Atrium names as they are.
- **Users are only created when `createUsers` is true** (it defaults to false).  Until then, someone with no matching
  Atrium user is reported and skipped, while linking, access levels, names and disabling carry on as usual.  When
  anyone is skipped this way, the page ends with a table of the enabled Atrium users nobody is linked to (name and GUID,
  sorted by surname; disabled users are left out while `ignoreDisabledUsers` is true), so the right one can be picked
  and its GUID put in that person's Extra Value by hand.
- **Change limits.**  A run that would exceed `changeLimit` writes applies nothing and says so.
- **Built-in and protected schedules (ids 0-5, read-only) are never modified.**
- **Dangerous commands need `confirm=True`** in code and `AtriumConfirm = "YES"` from a script; unlock time is capped at
  300 seconds.

## Things to know
- Atrium holds **5 access levels per user** and **100 periods per schedule**.  Overflows are reported, not silently cut.
- **Every Atrium request is a slow round trip**, and reading users and access levels walks each table by id.  Tables are
  read 100 ids per request (dropping to 25 if the controller refuses a wide range), a table that hasn't ended by id
  20,000 (1,000 for access levels and schedules) is an error that quotes the last record it read, and a range read
  that doesn't report which ids are in use is an error too.  A rule's `accessLevel` can be the level's numeric id
  instead of its name, which skips reading the level table at all.  `AtriumSync` stops with an error once reading has taken `timeBudgetSeconds` (default 60, `0`
  for none) so a web gateway doesn't time out first.  The page reports how long each phase took and how many requests it
  made.  A budget is for reading only; writes are not cut off halfway.  If it still runs long from a web page, run it
  from a scheduled task instead.
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
