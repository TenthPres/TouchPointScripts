# Design notes: not built yet

These are options and open questions for the two "consider, don't write" goals.  Nothing here has been implemented.

## 5. Card scans in TouchPoint (who was where, without asking Atrium)

**What the controller offers.**  The SDK has an Events group, and the vendor's SDK demo describes events as "saved on
the devices" and retrievable.  The object tables list a `syslog` type limited to 200 records, which hints that on-device
history is short and rolls over, but that has not been confirmed for door events.  The web UI also has an Events page.
Door events carry the card or user, the door and a timestamp.  Not yet examined: the exact event format, how events are
cursored (the SDK request builder has `last_ts_str`, `last_sernum`, `last_num` fields, which look like a resumable
cursor), and whether a user id or only a card number is present on each event.

**Recommended shape: poll and store.**
1. A scheduled script reads new events from every controller since the last cursor and keeps the cursor per controller
   in Special Content.  Poll often enough that the 200-record buffer cannot wrap between runs (to be measured on a busy day).
2. Events land in a **TouchPoint-side table** (custom SQL table via a script-installed schema, or `Meetings`/`Attend`
   where an event maps to a room reservation) with columns like: EventId (controller + sequence, unique), When, Door,
   AtriumUserId, CardNumber, Result (granted/denied/reason), PeopleId (resolved at import time via the link map).
   Store the raw card number too, so history survives a person being relinked.
3. Resolve PeopleId through `AtriumPeopleMap.json` at import; keep unresolved scans (visitors, contractors, shared codes)
   with PeopleId null rather than dropping them.

**Decisions needed.**
- *Attendance or just a log?*  Writing door scans to `Attend` would mix access control into attendance statistics.  A
  separate log table queried by SQL (and perhaps surfaced in a Blue Toolbar report) keeps them apart.
- *Privacy and retention.*  This is location tracking of identified people.  Decide who may query it, how long it is
  kept, and whether denied attempts are stored.
- *Door-to-place mapping.*  Doors need a table linking them to TouchPoint rooms/buildings for reporting.

**Risks.**  Buffer overrun if polling stalls; clock differences between controllers and TouchPoint; duplicates after a
cursor reset (hence the unique event id).

## 6. Card issuance and revocation from TouchPoint

**What the controller offers.**  `card` records (`cfg`: card number as `hexv5`/`hexv6`, format, owning `userId`, valid,
lost, stolen, activation/expiration, PIN option) can be added, written and deleted through the same SDK used elsewhere.
Today the controller has 340 cards.  There are also card-enrolment views in the UI (`users_T_cards_assign`), so the
controller can learn a card from a reader, but that has not been investigated for SDK use.

**Recommended shape: TouchPoint as the system of record for who holds which card.**
- Store card assignments in TouchPoint (a custom table, or an Extra Value on the person holding the card number(s)),
  with issue date, issuer and status (active, lost, revoked).
- A sync pass (same planner pattern as `AtriumSync`) makes the controller match: add missing cards bound to the linked
  Atrium user, flag lost/stolen (preferred over delete, so a stolen card shows up in the event log when used), and set
  expiration from the TouchPoint record.
- Revocation should be **instant and independent of the batch**: a button or script that sets `lost`/disables the card
  immediately, with the periodic sync as the safety net.  This is the part where a slow nightly job is not acceptable.

**Decisions needed.**
- *Where card numbers come from.*  Typing/scanning a number into TouchPoint, enrolling at a reader, or bulk import from
  the vendor.  Facility code and card format (`byte8`) must be captured correctly or the card will not read.
- *Who may issue and revoke*, and an audit trail of each change.
- *Ownership of existing cards.*  The 340 cards already on the controller need a one-time reconciliation against
  TouchPoint people before anything automatic is allowed to delete or disable them.
- *PIN codes* are secrets; decide whether TouchPoint ever holds them (recommendation: no).

**Risks.**  A sync bug that disables the wrong cards locks people out, so the same guards as `AtriumSync` apply (link by
GUID, change limits, dry-run default, refuse on suspicious empties), plus a never-touch list for emergency and
installer cards.
