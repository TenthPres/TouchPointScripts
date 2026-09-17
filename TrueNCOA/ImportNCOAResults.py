#Roles=Admin

# Import NCOA Results from TrueNCOA
#
# After you've uploaded the file from ExportForNCOA.py to TrueNCOA (https://truencoa.com) and it has finished
# processing, download the results file, open it in a text editor or Excel, and paste the full contents --
# including the header row -- into the box this script shows you.
#
# TrueNCOA's exact column names depend on your account setup (and any columns you send in are usually echoed back
# prefixed with "input_"). Rather than hard-coding one exact set of names, this script looks for header cells that
# *contain* one of the keywords in the lists below, so it should keep working even if your file's exact column
# names differ a bit. If it can't find a PeopleId column, or doesn't recognize any of the "did this person move"
# columns, it will tell you so you can add the right keyword to the matching list below and try again.
#
# This script never edits anyone's address automatically. NCOA match rates are good but not perfect, so instead it
# creates a Task/Note on each flagged person so a staff member can confirm the move before anyone changes the
# official record. Re-importing the same results file will not create duplicate tasks.

import csv
from StringIO import StringIO

# Who should the review tasks be assigned to. Defaults to whoever runs the import.
taskOwnerPid = model.UserPeopleId

# Extra Value used per-person to avoid creating a duplicate task for a row we've already imported.
lastImportEv = "TrueNCOA:LastMoveImport"

peopleIdHeaderKeywords = ["peopleid"]
moveIndicatorHeaderKeywords = ["movetype", "moveflag", "individualmoveindicator"]
moveDateHeaderKeywords = ["movedate", "moveeffectivedate"]
newAddressHeaderKeywords = ["addressline1", "newaddress", "standardizedaddress", "deliveryaddressline1"]
newAddress2HeaderKeywords = ["addressline2", "deliveryaddressline2"]
newCityHeaderKeywords = ["city"]
newStateHeaderKeywords = ["state"]
newZipHeaderKeywords = ["zip", "postalcode"]
footnoteHeaderKeywords = ["footnote", "returncode", "nixie", "vacant", "invalid", "undeliverable"]

model.Title = "Import NCOA Results"


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
    <p>Paste the full results file TrueNCOA sent you (including the header row) below, then click Import.</p>
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
        moveCol = findColumn(headers, moveIndicatorHeaderKeywords)
        moveDateCol = findColumn(headers, moveDateHeaderKeywords)
        addrCol = findColumn(headers, newAddressHeaderKeywords)
        addr2Col = findColumn(headers, newAddress2HeaderKeywords)
        cityCol = findColumn(headers, newCityHeaderKeywords)
        stateCol = findColumn(headers, newStateHeaderKeywords)
        zipCol = findColumn(headers, newZipHeaderKeywords)
        footnoteCol = findColumn(headers, footnoteHeaderKeywords)

        if pidCol is None:
            print "<p><b>Couldn't find a PeopleId column</b> in this file's headers: {0}</p>".format(", ".join(headers))
            print "<p>Make sure the PeopleId column from ExportForNCOA.py was set up as a passthrough/reference " \
                  "column in TrueNCOA and is present in this results file.</p>"
        else:
            print "<p>Matched columns &mdash; PeopleId: <b>{0}</b>, Move Type: <b>{1}</b>, Move Date: <b>{2}</b>, " \
                  "New Address: <b>{3}</b>, Footnote/Codes: <b>{4}</b></p>".format(
                      headers[pidCol],
                      headers[moveCol] if moveCol is not None else "(not found)",
                      headers[moveDateCol] if moveDateCol is not None else "(not found)",
                      headers[addrCol] if addrCol is not None else "(not found)",
                      headers[footnoteCol] if footnoteCol is not None else "(not found)")

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

                moveType = cell(row, moveCol)
                moveDate = cell(row, moveDateCol)
                newAddr = cell(row, addrCol)
                newAddr2 = cell(row, addr2Col)
                newCity = cell(row, cityCol)
                newState = cell(row, stateCol)
                newZip = cell(row, zipCol)
                footnote = cell(row, footnoteCol)

                signal = moveType or newAddr or footnote

                if not signal:
                    print "<tr><td>{0}</td><td>{1}</td><td>No move indicated</td></tr>".format(pid, p.Name)
                    continue

                flagged += 1

                dedupeKey = "|".join([moveType, moveDate, newAddr, newAddr2, newCity, newState, newZip, footnote])
                if model.ExtraValueText(pid, lastImportEv) == dedupeKey:
                    alreadyHandled += 1
                    print "<tr><td>{0}</td><td>{1}</td><td>Already imported previously, skipped</td></tr>".format(pid, p.Name)
                    continue

                noteBody = (
                    "TrueNCOA indicates this person may have moved.\n\n"
                    "Move Type: {0}\n"
                    "Move Date: {1}\n"
                    "New Address: {2} {3} {4} {5} {6}\n"
                    "Footnote/Codes: {7}\n\n"
                    "Please confirm with the person before updating their address in TouchPoint."
                ).format(moveType or "(unknown)", moveDate or "(unknown)", newAddr, newAddr2, newCity, newState,
                         newZip, footnote or "(none)")

                model.CreateTaskNote(taskOwnerPid, pid, None, None, True, None, noteBody, None, [])
                model.AddExtraValueText(pid, lastImportEv, dedupeKey)
                createdTasks += 1

                print "<tr><td>{0}</td><td><a href=\"/Person2/{0}/\">{1}</a></td><td>Task created for review</td></tr>".format(pid, p.Name)

            print "</table>"

            print "<p>{0} people flagged as possible moves. {1} new review tasks created. " \
                  "{2} were already imported previously and skipped.</p>".format(flagged, createdTasks, alreadyHandled)

            if notFound:
                print "<p>Could not find a TouchPoint person for these PeopleIds: {0}</p>".format(
                    ", ".join(str(x) for x in notFound))
