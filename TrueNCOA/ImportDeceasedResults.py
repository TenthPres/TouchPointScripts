#Roles=Admin

# Import Deceased Results from TrueDeceased (or TrueNCOA's Deceased Identification add-on)
#
# After you've uploaded the file from ExportForNCOA.py to TrueDeceased (https://truedeceased.com), or run TrueNCOA's
# Deceased Identification (DI) service on it, download the results/match file and paste its full contents --
# including the header row -- into the box this script shows you.
#
# Like ImportNCOAResults.py, this looks for header cells that *contain* one of the keywords below rather than
# requiring an exact column name match, since the exact names depend on your account setup. If it can't find a
# PeopleId column, it will tell you so you can add the right keyword below and try again.
#
# This script never marks anyone Deceased automatically. A deceased match here removes the person from mailing and
# calling in a lot of workflows, so it should always be confirmed by a human first. Instead, it creates a Task/Note
# on each matched person so a staff member can verify (an obituary, a call to the family, etc.) before anyone
# updates the official record. Re-importing the same results file will not create duplicate tasks.

import csv
from StringIO import StringIO

# Who should the review tasks be assigned to. Defaults to whoever runs the import.
taskOwnerPid = model.UserPeopleId

# Extra Value used per-person to avoid creating a duplicate task for a row we've already imported.
lastImportEv = "TrueNCOA:LastDeceasedImport"

peopleIdHeaderKeywords = ["peopleid"]
deceasedFlagHeaderKeywords = ["deceased", "diresult", "matchcode", "deathindicator"]
dateOfDeathHeaderKeywords = ["dateofdeath", "dod", "deceaseddate"]
obituaryHeaderKeywords = ["obituary", "obit"]
sourceHeaderKeywords = ["source", "matchsource", "dataSource"]

model.Title = "Import Deceased Results"


def normalize(header):
    return header.lower().replace(" ", "").replace("_", "").replace("-", "")


def findColumn(headers, keywords):
    normalized = [normalize(h) for h in headers]
    for keyword in keywords:
        nk = normalize(keyword)
        for i, h in enumerate(normalized):
            if nk in h:
                return i
    return None


def cell(row, idx):
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


if model.HttpMethod != "post" or Data.csvText == "":
    print """
    <p>Paste the full results/match file from TrueDeceased (or TrueNCOA's Deceased Identification add-on),
    including the header row, below, then click Import.</p>
    <form method="post" action="">
        <textarea name="csvText" style="width:100%;height:300px;"
            placeholder="PeopleId,input_FirstName,...&#10;123,John,..."></textarea>
        <p><button type="submit">Import</button></p>
    </form>
    """
else:
    reader = csv.reader(StringIO(Data.csvText.encode('utf-8')))
    rows = [r for r in reader if any(c.strip() != "" for c in r)]

    if len(rows) < 2:
        print "<p>That didn't look like a CSV with a header row and at least one data row. Please try again.</p>"
    else:
        headers = rows[0]
        dataRows = rows[1:]

        pidCol = findColumn(headers, peopleIdHeaderKeywords)
        deceasedCol = findColumn(headers, deceasedFlagHeaderKeywords)
        dodCol = findColumn(headers, dateOfDeathHeaderKeywords)
        obitCol = findColumn(headers, obituaryHeaderKeywords)
        sourceCol = findColumn(headers, sourceHeaderKeywords)

        if pidCol is None:
            print "<p><b>Couldn't find a PeopleId column</b> in this file's headers: {0}</p>".format(", ".join(headers))
            print "<p>Make sure the PeopleId column from ExportForNCOA.py was set up as a passthrough/reference " \
                  "column and is present in this results file.</p>"
        else:
            print "<p>Matched columns &mdash; PeopleId: <b>{0}</b>, Deceased Match: <b>{1}</b>, " \
                  "Date of Death: <b>{2}</b>, Obituary Link: <b>{3}</b></p>".format(
                      headers[pidCol],
                      headers[deceasedCol] if deceasedCol is not None else "(not found)",
                      headers[dodCol] if dodCol is not None else "(not found)",
                      headers[obitCol] if obitCol is not None else "(not found)")

            if deceasedCol is None and dodCol is None:
                print "<p>This file doesn't have a recognizable deceased-match column, so every row would be " \
                      "treated as \"no match\". Add the right keyword to deceasedFlagHeaderKeywords or " \
                      "dateOfDeathHeaderKeywords at the top of this script and try again.</p>"

            flagged = 0
            createdTasks = 0
            alreadyHandled = 0
            notFound = []

            print "<table border=\"1\" cellpadding=\"4\"><tr><th>PeopleId</th><th>Name</th><th>Result</th></tr>"

            for row in dataRows:
                pidText = cell(row, pidCol)
                if not pidText.isdigit():
                    continue

                pid = int(pidText)
                p = model.GetPerson(pid)
                if p is None:
                    notFound.append(pid)
                    continue

                deceasedFlag = cell(row, deceasedCol)
                dateOfDeath = cell(row, dodCol)
                obituary = cell(row, obitCol)
                source = cell(row, sourceCol)

                signal = deceasedFlag or dateOfDeath

                if not signal:
                    print "<tr><td>{0}</td><td>{1}</td><td>No deceased match</td></tr>".format(pid, p.Name)
                    continue

                if p.Deceased:
                    print "<tr><td>{0}</td><td>{1}</td><td>Already marked Deceased in TouchPoint, skipped</td></tr>".format(pid, p.Name)
                    continue

                flagged += 1

                dedupeKey = "|".join([deceasedFlag, dateOfDeath, obituary, source])
                if model.ExtraValueText(pid, lastImportEv) == dedupeKey:
                    alreadyHandled += 1
                    print "<tr><td>{0}</td><td>{1}</td><td>Already imported previously, skipped</td></tr>".format(pid, p.Name)
                    continue

                noteBody = (
                    "A deceased-record service found a possible match for this person.\n\n"
                    "Match/Result: {0}\n"
                    "Date of Death: {1}\n"
                    "Obituary Link: {2}\n"
                    "Source: {3}\n\n"
                    "Please verify (an obituary, family, or the Social Security Death Index) before marking "
                    "this person Deceased in TouchPoint."
                ).format(deceasedFlag or "(unknown)", dateOfDeath or "(unknown)", obituary or "(none)",
                         source or "(unknown)")

                model.CreateTaskNote(taskOwnerPid, pid, None, None, True, None, noteBody, None, [])
                model.AddExtraValueText(pid, lastImportEv, dedupeKey)
                createdTasks += 1

                print "<tr><td>{0}</td><td><a href=\"/Person2/{0}/\">{1}</a></td><td>Task created for review</td></tr>".format(pid, p.Name)

            print "</table>"

            print "<p>{0} people flagged as possible deceased matches. {1} new review tasks created. " \
                  "{2} were already imported previously and skipped.</p>".format(flagged, createdTasks, alreadyHandled)

            if notFound:
                print "<p>Could not find a TouchPoint person for these PeopleIds: {0}</p>".format(
                    ", ".join(str(x) for x in notFound))
