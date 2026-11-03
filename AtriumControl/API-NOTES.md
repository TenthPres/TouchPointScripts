# CDVI Atrium API notes (firmware 5.00.0583, A22M)

How the Atrium SDK works, as established by reading the controller's own bundled SDK demo code and confirming with
requests against the production system.  Vendor documentation is thin: the public wiki page
["HOW-TO - Use the SDK demo"](https://mrdltd.atlassian.net/wiki/spaces/PUB/pages/35061795/HOW-TO+-+Use+the+SDK+demo)
describes three groups (Records, Commands, Events) but not the XML.

## Status legend
**verified live** = done against the real controller.  **inferred** = read from the demo's code, never sent.

## Session and encryption (verified live)
- `GET /login_sdk.xml` returns a temporary `session` and the master `serial`.
- `key = MD5(serial + session).upper()`.  Login is `POST /login_sdk.xml` with `sid`, `cmd=login`,
  `login_user = RC4hex(key, username)`, `login_pass = MD5(key + password).upper()`.
- **A failed login still answers 200.**  Success is `SDK_CFG user_id >= 0` with a username; `-1` with empty username
  means not authenticated.  The account needs "SDK login" enabled.
- Sessions last 900 s.  Responses are plain XML or `post_enc=<RC4 hex>&post_chk=<16-bit char sum, hex>`; requests that
  carry a body are sent in the same encrypted form.  The same key serves both directions.

## The SDK endpoint (verified live)
`POST /sdk.xml?_=<n>&sid=<session>`, body = `encrypt(xml)`:

```xml
<?xml version="1.0" encoding="utf-8"?><SDK xmlns='https://www.cdvi.ca/'><RECORDS>
  <REC trans_id='1' cmd='read' sernum='00009F90' type='user' id='304' rec='cfg'></REC>
</RECORDS></SDK>
```
- Omitting the XML declaration or sending the wrong shape gives **HTTP 404**, not a helpful error.
- `cmd` is `read`, `write`, `add`, `delete` or `info`.  Use `id` for one record or `id_min`/`id_max` for a range; a range
  returns one `<DATA>` per id, with `obj_status="used"` or `"free"`.
- `<DATA>` carries fields as attributes, array fields as `word24_0` ... `word24_4`.  Writes send only the fields named.
- `sernum` selects the controller (master `00009F90`, or a slave's serial for its own objects).
- Responses declare a default namespace; strip it before using ElementTree.
- Reads, a rename/restore and an access-level add/remove on a test user were all verified live.

## Record layouts used (verified live unless noted)
| Type (id) | Fields |
| --- | --- |
| `user` (11) `cfg` | `label3` first, `label4` last, `guid2`, `valid`, `utc_time22` activation, `utc_time23` expiration (hex epoch, `FFFFFFFF` = never), `word24_0..4` access levels (`65535` = empty), `word26_0..4` floor levels, option bits `bit5..bit20` |
| `access_lvl` (24) `cfg` | `label3`, `word4_*` schedule per area |
| `sched` (22) `cfg` | `label3`, `utc_time4` cycle start, `dword5` cycle seconds (604800 = weekly), `dword6_i` / `dword7_i` period start/stop offsets in seconds (up to 100), plus inclusion/exclusion bitfields.  Writing `utc_time4`, `dword5` and all 100 offset pairs verified live; unused pairs are zeroed.  Start time is controller local wall time written as if UTC: every existing schedule's start decodes to exactly 00:00:00 UTC, which would not be so if it were true UTC (confirmed from stored data; not observed against a door opening). |
| `card` (12) `cfg` | `label3`, `dword4` user id, `hexv5`/`hexv6` card number, `byte8` format, `bit21` lost, `bit22` stolen, `utc_time24/25` activation/expiry |
| `ir_apm` (66) `status` | wireless lock: `byte0`/`byte1` battery volts + fraction, `bit5` online |
| `ir_apm` (66) `trouble` | `bit1` battery low, `bit2` battery critical, `bit5` RF loss |

## Commands
Commands use `<COMMANDS><CMD trans_id cmd sernum type id>` with parameters in `<DATA>`; no `rec` attribute is needed.
- **Verified live:** `door` `unlock` with `<DATA dword0='5'/>` on a spare door.  The controller answered `res="ok"`, the
  door's `status` record changed for about a second and returned to normal on its own after the 5 seconds.
  ```xml
  <CMD trans_id='2' cmd='unlock' sernum='0000A373' type='door' id='1'><DATA dword0='5'/></CMD>
  ```
- Inferred, **not sent**: `door` `lock`/`enable`/`disable`/`override`; `lockdown` (89) `start`, `stop`, `start_pc`,
  `stop_pc` (optional `utf0` password).  The lockdown calls use the same request shape as the verified unlock.

## Other things on the controller (read-only, verified live)
- `GET /devices.xml` (6 controllers besides the master), `/doors.xml` (20 doors), `/schedules.xml`, `/access_levels.xml`,
  `/info_T_schlage.xml?T_serial=<sn>`.  These are the web UI's REST pages; they return the same data the SDK does.
- Wireless (Allegion/Schlage NDE) locks are only on controller `B000094F` (3 enabled).  Their trouble flags are the
  authoritative battery signal.  The voltage fraction scale is an assumption (1/256 V).

## What the controller does NOT store
Users have only name, GUID, flags, dates, access levels, language and floors.  **No email, phone, notes or custom fields.**
Whatever else the desktop software shows per person must live in that software's own database.

## Mistakes in the first starter (now replaced)
`users_sdk.xml`, `schedules_sdk.xml`, `events_sdk.xml`, `records_sdk.xml` do not exist (404); the `list_users`,
`add_event` and similar commands were guesses.
