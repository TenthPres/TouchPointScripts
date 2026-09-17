# TrueNCOA / TrueDeceased Address & Deceased Checks

Compare people in TouchPoint against [TrueNCOA](https://truencoa.com) (USPS National Change of Address processing)
and [TrueDeceased](https://truedeceased.com) (deceased record suppression), and get a review Task on anyone who may
have moved or passed away.

TrueNCOA/TrueDeceased are third-party, paid, USPS-licensed services. This tool does not call their API directly,
because the exact endpoints, authentication, and result column names TrueNCOA hands out are account-specific and
change over time (they publish an Input/Output File Guide and a Postman collection per account). Instead, these
scripts handle the TouchPoint side of a simple, safe loop:

1. **Export** the people you want checked, in a CSV TrueNCOA/TrueDeceased can read.
2. You upload that CSV through TrueNCOA's/TrueDeceased's own web portal (or their CLI/API, if you've set that up)
   and download the results once processing finishes.
3. **Import** the results back into TouchPoint. Matches don't get applied automatically -- each one becomes a Task
   assigned for a staff member to confirm before anyone's address or Deceased status actually changes.

## Scripts

- **[ExportForNCOA.py](ExportForNCOA.py)** -- A Python Script you run from the Blue Toolbar (`</>` menu) against
  any Search or other people list. It builds a CSV with each person's `PeopleId`, name, and mailing address, and
  gives you a "Download CSV" button.
- **[ImportNCOAResults.py](ImportNCOAResults.py)** -- A Python Script (run directly, not from the Blue Toolbar).
  Paste in the results file TrueNCOA sends back after processing. It matches rows back to people by `PeopleId` and
  creates a review Task on anyone flagged as having moved.
- **[ImportDeceasedResults.py](ImportDeceasedResults.py)** -- The same idea, for TrueDeceased's (or TrueNCOA's
  Deceased Identification add-on's) results file. Creates a review Task on anyone flagged as a possible deceased
  match.

## How to Install

1. In the Special Content section of TouchPoint, create three new **Python Script** documents named
   `ExportForNCOA`, `ImportNCOAResults`, and `ImportDeceasedResults` (or whatever names you prefer), and paste in
   the matching file from this folder.
2. Restrict all three to the Admin role (or whichever role should be trusted with everyone's mailing address --
   the `#Roles=Admin` line at the top of each script is TouchPoint's own role-restriction directive).
3. Add `ExportForNCOA` to the Blue Toolbar's "Other Reports" / Python Script menu so it's available from any
   Search.

## How to Run

1. Build a Search (or other people list) in TouchPoint for whoever you want checked -- e.g. "everyone with an
   address, not already flagged Deceased." From the Blue Toolbar, run `ExportForNCOA` and download the CSV.
2. Upload that CSV to TrueNCOA for an NCOA move-update pass, and/or to TrueDeceased for a deceased-suppression
   pass. Both services let you map your own column headers to their fields during upload, so `ExportForNCOA.py`'s
   headers don't need to match their documentation exactly -- the one thing to set up is having TrueNCOA/TrueDeceased
   treat the `PeopleId` column as a passthrough reference/keycode column, so it comes back untouched in your
   results.
3. Once processing is done, download the results file(s) and run `ImportNCOAResults` and/or
   `ImportDeceasedResults`, pasting in the full file (header row included).
4. Work the review Tasks the import creates. Each one shows what TrueNCOA/TrueDeceased found; nothing in TouchPoint
   changes until a staff member confirms it and updates the person's record by hand.

## Why nothing is applied automatically

NCOA and deceased-suppression matching is good, but it's a probabilistic match against a national database, not a
confirmation. A bad match on either could mean overwriting a valid address or, worse, marking a living person
Deceased (which, per [MemberAutomation](../MemberAutomation), can drop their membership and clear their email
addresses). These scripts are intentionally "compare and flag for review," not "auto-update" -- the Task/Note
pattern mirrors how [PrayerSmsHandler](../PrayerSmsHandler) and [IncomingEmail](../IncomingEmail) hand things off to
a person rather than acting unattended.

## Adjusting the results column matching

`ImportNCOAResults.py` and `ImportDeceasedResults.py` don't hard-code TrueNCOA's/TrueDeceased's exact output
column names, since those vary by account and change over time. Instead, each script looks for header cells that
*contain* a keyword (e.g. `movetype`, `dateofdeath`) from a list defined near the top of the file. If a script
tells you it couldn't find a column it needed, open your results file, find the real header name, and add a
matching keyword to the relevant list.
