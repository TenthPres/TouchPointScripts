# TrueNCOA / TrueDeceased Address & Deceased Checks

Compare people in TouchPoint against [TrueNCOA](https://truencoa.com) (USPS National Change of Address
processing) and [TrueDeceased](https://truedeceased.com) (deceased record suppression), and get a review Task on
anyone who may have moved or passed away.

## TrueNCOA: a real API integration

`SubmitToNCOA.py` and `CheckNCOAStatus.py` call TrueNCOA's HTTP API directly -- no manual file upload/download
needed. They're based on TrueNCOA's own official CLI tool, [truencoa/cli](https://github.com/truencoa/cli) (its
`Program.cs`), since that's the most concrete, current reference available for how the API is actually called;
TrueNCOA's account-specific Postman collection and Input/Output File Guide (linked from
[truencoa.com/api](https://truencoa.com/api/)) are the authoritative source and worth reading if anything here
doesn't match what you see.

What the CLI's source shows, and what these scripts do with it:

- **Auth** is two plain HTTP headers, `user_name` and `password` -- your TrueNCOA account email and password, not
  an API key or Bearer token.
- **Base URL** is `https://api.truencoa.com/` for production, `https://api.testing.truencoa.com/` for testing.
- **Uploading records** is `POST files/{fileName}/records`, body `application/x-www-form-urlencoded`, with each
  record's fields appended as repeated key/value pairs (the CLI reads them straight from your input file's
  header row with no renaming). The recognized field names, per the CLI's README, are `individual_id`,
  `individual_first_name`, `individual_last_name`, `address_line_1`, `address_line_2`, `address_city_name`,
  `address_state_code`, and `address_postal_code`. `individual_id` is set to the person's TouchPoint `PeopleId`
  so results can be matched back to the right person.
- **Finalizing the upload** is `PATCH files/{fileName}?status=submit`, which tells TrueNCOA to start NCOA
  processing.
- **Checking progress** is `GET files/{fileName}`, whose `Status` moves through `Mapped`/`Processing` to
  `Processed` (or `Cancelled`/`Errored`).
- **Exporting results**, once `Processed`, is `PATCH files/{fileName}?status=export&suppress={bool}`, which
  returns a *different* file id (`Id` in the response) for the export job -- that one goes through its own
  `Export`/`Exporting` -> done `Status` cycle.
- **Downloading results** is `GET files/{exportFileId}/records?page={n}&charge={bool}`, paged until a page comes
  back with no records. The CLI's `Record` fields include `move_applied`, `move_type`, `move_date`,
  `move_distance`, and standardized address fields (`street_number`, `street_name`, `street_suffix`, `city_name`,
  `state_code`, `postal_code`), plus `match_flag`/`nxi`/`address_status`/`error_number`.

Since NCOA processing happens on TrueNCOA's side and isn't instant, the work is split into two scripts instead of
one that waits around:

- **[SubmitToNCOA.py](SubmitToNCOA.py)** -- run from the Blue Toolbar (`</>` menu) against any Search or other
  people list. Uploads everyone selected and marks the file submitted. Remembers what it submitted in a small
  tracking document (`TrueNCOA-Files.json`, a Special Content text document) so the next script knows what to
  check on.
- **[CheckNCOAStatus.py](CheckNCOAStatus.py)** -- run directly (not from the Blue Toolbar), whenever you want to
  check progress -- e.g. once a day. Advances each submitted file one step (still processing / trigger export /
  export still running / download and import), and creates a review Task on anyone the results flag as having
  moved.
- **[Install.py](Install.py)** -- run once, after the two scripts above already exist as Special Content
  documents. Adds `CheckNCOAStatus` to TouchPoint's Morning Batch (the same mechanism
  [SchedulerSyncer](../SchedulerSyncer), [Mapify](../Mapify), and [NonweeklyMeetings](../NonweeklyMeetings) use to
  run themselves daily) so it checks -- and re-checks -- automatically, with no one needing to remember to run it.

### Taking advantage of TrueNCOA's free re-checks

TrueNCOA automatically keeps re-processing your file against new NCOA moves for a while after you submit it --
their site calls this "free weekly NCOA updates," and says it's free for 90-95 days for accounts with
501(c)(3) status (most churches qualify) as of a 5/1/2023 policy change. Rather than relying on a staff member
noticing TrueNCOA's notification emails and downloading updates by hand, `CheckNCOAStatus.py` keeps a submitted
file in a "watching" state and re-exports/re-checks it once a day (via Install.py's Morning Batch hook) for
`freeUpdateWindowDays` (90, by default) from its submission date, creating a Task for anything newly flagged.
Re-checking is safe to repeat since the per-person dedupe (`TrueNCOA:LastMoveImport`) means only genuinely new
matches ever create a new Task.

That said, *how* TrueNCOA's backend actually surfaces those free re-checks wasn't something the CLI source (or
anything else reachable while writing this) confirmed. Their own docs describe the update as showing up as a
separately-named file in their portal (e.g. `your file name - Updated 20260101`) that you'd otherwise find by
hand, rather than the original file's export simply reflecting new data when you ask for it again. If, after
running for a while, `CheckNCOAStatus.py` never reports new moves but TrueNCOA's portal or notification emails
show update files it isn't picking up, that's the mechanism actually in play -- check with TrueNCOA support for
how those update files are named/addressed via the API, and adjust `triggerExport()`/`downloadRecords()` in
`CheckNCOAStatus.py` to fetch that file instead of (or in addition to) re-exporting the original.

Submitting a *new* file (a new NCOA processing charge, per TrueNCOA's pricing) is still a manual, deliberate
action -- run `SubmitToNCOA` again from the Blue Toolbar whenever you want a fresh full check, e.g. for people who
weren't part of an earlier submission.

One caveat: this repo hasn't needed to make an HTTP `PATCH` request anywhere else, so `model.RestPatch` (used for
the `status=submit` and `status=export` calls) isn't a confirmed part of TouchPoint's Python Script API the way
`model.RestGet`/`model.RestPost`/`model.RestPostJson` are (see `ConstantContact.py`, `Mailchimp/MailchimpSync.py`
for those in use). If that method doesn't exist in your TouchPoint version, check TouchPoint's Python Script API
reference (or ask TouchPoint support) for the right way to send a PATCH request, and swap it into both scripts.

Similarly, the exact field names in the *results* (`move_type`, `street_name`, etc.) come from the CLI's source,
not TrueNCOA's account-specific docs -- if `CheckNCOAStatus.py`'s report shows people flagged with a blank "New
Address" when you know TrueNCOA found one, open `importRecords()` in that script and adjust the field names to
match what your account's export actually returns.

## TrueDeceased: manual export/import

TrueDeceased is a separate product from TrueNCOA, with its own account and portal, and doesn't appear to be part
of TrueNCOA's API/CLI. Without a similarly concrete reference for its API, this stays a manual, file-based
loop instead:

- **[ExportForDeceasedCheck.py](ExportForDeceasedCheck.py)** -- run from the Blue Toolbar against any Search or
  other people list. Builds a CSV (name, address, email, phone -- everything TrueDeceased says it can match on)
  with a "Download CSV" button.
- **[ImportDeceasedResults.py](ImportDeceasedResults.py)** -- run directly. Paste in the results file
  TrueDeceased (or TrueNCOA's Deceased Identification add-on) sends back, including its header row. It matches
  rows back to people by the `PeopleId` column and creates a review Task on anyone flagged as a possible
  deceased match. Since TrueDeceased's exact result column names weren't available either, it matches by keyword
  (e.g. anything containing `deceased` or `dateofdeath`) rather than requiring an exact column name -- if it
  can't find what it needs, it says so, and the keyword lists at the top of the file can be extended to match.

## How to Install

1. In the Special Content section of TouchPoint, create five new **Python Script** documents --
   `SubmitToNCOA`, `CheckNCOAStatus`, `Install`, `ExportForDeceasedCheck`, and `ImportDeceasedResults` (or
   whatever names you prefer, as long as `SubmitToNCOA.py`/`CheckNCOAStatus.py`/`Install.py` keep matching the
   `model.CallScript(...)` names inside each other) -- and paste in the matching file from this folder.
2. Restrict all of them to the Admin role (or whichever role should be trusted with everyone's mailing address --
   the `#Roles=Admin` line at the top of each script is TouchPoint's own role-restriction directive).
3. Fill in your TrueNCOA account email/password at the top of `SubmitToNCOA.py` and `CheckNCOAStatus.py` (keep
   the two in sync). Start with `https://api.testing.truencoa.com/` as the base URL until you've confirmed things
   work.
4. Add `SubmitToNCOA` and `ExportForDeceasedCheck` to the Blue Toolbar's "Other Reports" / Python Script menu so
   they're available from any Search.
5. Run `Install` once (it adds `CheckNCOAStatus` to the Morning Batch, then runs it immediately).

## How to Run

1. Build a Search (or other people list) in TouchPoint for whoever you want checked -- e.g. "everyone with an
   address, not already flagged Deceased."
2. For an NCOA move check: run `SubmitToNCOA` from the Blue Toolbar. From there, Morning Batch runs
   `CheckNCOAStatus` automatically every day (once `Install` has been run) -- it reports "still processing" until
   TrueNCOA is done, then imports results and keeps re-checking for new moves during TrueNCOA's free-update
   window (see above), all without anyone needing to run anything by hand. You can also run `CheckNCOAStatus`
   directly any time you don't want to wait for the next Morning Batch. Either way, work the review Tasks it
   creates.
3. For a deceased check: run `ExportForDeceasedCheck` from the Blue Toolbar and download the CSV, upload it to
   TrueDeceased (or run TrueNCOA's Deceased Identification add-on on it) through their own portal, and once
   processing is done, run `ImportDeceasedResults` and paste in the results file. Work the review Tasks it
   created. (TrueDeceased processes weekly on its own, but since this script doesn't have its API to check
   automatically, this half stays manual.)
4. Either way: nothing in TouchPoint changes until a staff member confirms the Task and updates the person's
   record by hand.

## Why nothing is applied automatically

NCOA and deceased-suppression matching is good, but it's a probabilistic match against a national database, not
a confirmation. A bad match on either could mean overwriting a valid address or, worse, marking a living person
Deceased (which, per [MemberAutomation](../MemberAutomation), can drop their membership and clear their email
addresses). These scripts are intentionally "compare and flag for review," not "auto-update" -- the Task/Note
pattern mirrors how [PrayerSmsHandler](../PrayerSmsHandler) and [IncomingEmail](../IncomingEmail) hand things off
to a person rather than acting unattended.
