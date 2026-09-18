#Roles=Admin

# Check TrueNCOA Processing Status, Export, and Import Results
#
# Run this periodically after running SubmitToNCOA.py -- or better, run Install.py once so it's added to
# TouchPoint's Morning Batch and checks itself automatically every day. Each time it runs, it looks at every file
# SubmitToNCOA.py has submitted and advances it one step:
#   - Still processing on TrueNCOA's side? Reports that and does nothing else yet.
#   - Finished NCOA processing ("Processed")? Triggers TrueNCOA's export step.
#   - Export still running? Reports that and does nothing else yet.
#   - Export finished? Downloads the results and creates a review Task on anyone flagged as having moved.
#
# TrueNCOA automatically keeps re-checking your file against new NCOA moves for a while after you submit it (its
# own site calls this "free weekly NCOA updates," advertised as free for 90-95 days for accounts with 501(c)(3)
# status -- see https://truencoa.com/keep-your-addresses-up-to-date-with-free-weekly-ncoa-updates/). To take
# advantage of that automatically instead of relying on someone noticing TrueNCOA's notification emails, this
# script doesn't stop after the first import: it keeps re-exporting and re-checking the same file once a day
# (whenever Morning Batch runs it) until freeUpdateWindowDays has passed since it was submitted. Re-checking is
# safe to repeat -- the per-person dedupe below means only genuinely new matches create a new Task.
#
# Whether re-running TrueNCOA's export step on an already-processed file is really how their backend surfaces
# those free re-checks isn't confirmed (TrueNCOA's own docs describe the update showing up as a separately named
# file you'd otherwise find by hand in their portal, e.g. "your file name - Updated 20260101"). If, after this
# has been running a while, you notice TrueNCOA's portal has update files this script isn't picking up, that's
# the mechanism it's actually using -- check with TrueNCOA support and adjust triggerExport()/downloadRecords()
# accordingly.
#
# This follows the same HTTP API TrueNCOA's own CLI tool uses -- see https://github.com/truencoa/cli (Program.cs)
# for the reference implementation this is based on, since TrueNCOA's account-specific Postman/API docs weren't
# reachable while writing this. The field names below (move_type, street_name, etc.) come from that source too;
# if TrueNCOA's actual response uses different names, the "New Address" column in the report below will come up
# blank even when TrueNCOA found a move, which is your cue to fix the field names in importRecords() below.
#
# This never edits anyone's address automatically -- NCOA match rates are good but not perfect, so a Task is
# created for a staff member to confirm the move first. Re-running this script won't create duplicate tasks for
# a file it's already imported.

import json
import urllib
from datetime import datetime, timedelta

# ##################### #
# Configuration -- keep the credentials in sync with SubmitToNCOA.py
# ##################### #

trueNcoaUserName = "YOUR TRUENCOA ACCOUNT EMAIL"
trueNcoaPassword = "YOUR TRUENCOA PASSWORD"
trueNcoaBaseUrl = "https://api.truencoa.com/"

registryContentName = "TrueNCOA-Files.json"

# Whether to ask TrueNCOA to suppress (leave out) records where no move was found from the exported results.
# False is the safer default while you're getting started, since it means you'll see -- and can spot-check --
# records with no move too, rather than trusting the suppression sight-unseen.
suppressNonMovers = False

# Whether to allow TrueNCOA to bill your account for this download. Leave False until you've confirmed with
# TrueNCOA how downloads are billed; if downloads come back empty, this may need to be True instead.
allowCharge = False

# Who the review tasks get assigned to. Defaults to whoever runs this script. If Morning Batch is running this
# script automatically (see Install.py), model.UserPeopleId won't be a real staff member -- set this to a
# specific PeopleId instead.
taskOwnerPid = model.UserPeopleId

# Extra Value used per-person to avoid creating a duplicate task for a record we've already imported.
lastImportEv = "TrueNCOA:LastMoveImport"

# How many days after submitting a file to keep automatically re-checking it for new moves, taking advantage of
# TrueNCOA's free re-check window. TrueNCOA's own pages say 90-95 days for accounts with 501(c)(3) status (most
# churches qualify); 90 is used here to stay safely inside that. After this many days, a file is left alone.
freeUpdateWindowDays = 90

# NOTE: model.RestPatch is used below for the HTTP PATCH calls TrueNCOA's API requires. This repo hasn't needed
# a PATCH call anywhere else, so it's not confirmed that TouchPoint's Python Script API actually exposes a
# method by that name -- see the same note in SubmitToNCOA.py. If this errors out on that line, check
# TouchPoint's Python Script API reference (or ask TouchPoint support) for the right way to send an HTTP PATCH
# request, and swap it in here too.

# All done configuring. On to the code.
############################################################################################

model.Title = "Check TrueNCOA Status"


def authHeaders(extra=None):
    headers = {
        "user_name": trueNcoaUserName,
        "password": trueNcoaPassword,
    }
    if extra:
        headers.update(extra)
    return headers


def loadRegistry():
    text = model.TextContent(registryContentName)
    return json.loads(text) if text else {"files": []}


def saveRegistry(registry):
    model.WriteContent(registryContentName, json.dumps(registry, indent=2))


def getFile(name):
    url = "{0}files/{1}".format(trueNcoaBaseUrl, name)
    return json.loads(model.RestGet(url, authHeaders()))


def triggerExport(fileEntry):
    url = "{0}files/{1}?status=export&suppress={2}".format(
        trueNcoaBaseUrl, fileEntry["fileName"], "true" if suppressNonMovers else "false")
    response = json.loads(model.RestPatch(url, authHeaders(), ""))
    fileEntry["exportFileId"] = response.get("Id")
    fileEntry["status"] = "exporting"


def downloadRecords(exportFileId):
    records = []
    page = 1
    while True:
        url = "{0}files/{1}/records?page={2}&charge={3}".format(
            trueNcoaBaseUrl, exportFileId, page, "true" if allowCharge else "false")
        response = json.loads(model.RestGet(url, authHeaders()))
        pageRecords = response.get("Records", [])
        if not pageRecords:
            break
        records.extend(pageRecords)
        page += 1
    return records


def firstNonEmpty(record, keys):
    for k in keys:
        v = record.get(k)
        if v:
            return v
    return ""


def freeUpdatesExpired(fileEntry):
    submittedDate = fileEntry.get("submittedDate")
    if not submittedDate:
        return True
    submitted = datetime.strptime(submittedDate, "%Y-%m-%d %H:%M:%S")
    return datetime.now() > submitted + timedelta(days=freeUpdateWindowDays)


def importRecords(fileEntry, records):
    flagged = 0
    createdTasks = 0
    alreadyHandled = 0
    notFound = []

    for record in records:
        pidText = unicode(firstNonEmpty(record, ["individual_id", "input_individual_id"]))
        if not pidText.isdigit():
            continue

        pid = int(pidText)
        p = model.GetPerson(pid)
        if p is None:
            notFound.append(pid)
            continue

        moveApplied = firstNonEmpty(record, ["move_applied"])
        moveType = firstNonEmpty(record, ["move_type"])
        moveDate = firstNonEmpty(record, ["move_date"])
        newAddr = " ".join(unicode(record.get(k, "")) for k in
                            ["street_number", "street_name", "street_suffix"]).strip()
        newCity = firstNonEmpty(record, ["city_name"])
        newState = firstNonEmpty(record, ["state_code"])
        newZip = firstNonEmpty(record, ["postal_code"])
        addressStatus = firstNonEmpty(record, ["address_status"])

        signal = moveApplied or moveType or newAddr

        if not signal:
            continue

        flagged += 1

        dedupeKey = "|".join([unicode(moveApplied), unicode(moveType), unicode(moveDate), newAddr,
                               unicode(newCity), unicode(newState), unicode(newZip), unicode(addressStatus)])
        if model.ExtraValueText(pid, lastImportEv) == dedupeKey:
            alreadyHandled += 1
            continue

        noteBody = (
            "TrueNCOA indicates this person may have moved.\n\n"
            "Move Applied: {0}\n"
            "Move Type: {1}\n"
            "Move Date: {2}\n"
            "New Address: {3} {4} {5} {6}\n"
            "Address Status: {7}\n\n"
            "Please confirm with the person before updating their address in TouchPoint."
        ).format(moveApplied or "(unknown)", moveType or "(unknown)", moveDate or "(unknown)",
                 newAddr, newCity, newState, newZip, addressStatus or "(none)")

        model.CreateTaskNote(taskOwnerPid, pid, None, None, True, None, noteBody, None, [])
        model.AddExtraValueText(pid, lastImportEv, dedupeKey)
        createdTasks += 1

    # Cumulative across every check of this file, not just this run, since a file gets re-checked repeatedly
    # during its free-update window.
    summary = fileEntry.setdefault("importSummary", {
        "flagged": 0, "createdTasks": 0, "alreadyHandled": 0, "notFound": [],
    })
    summary["flagged"] += flagged
    summary["createdTasks"] += createdTasks
    summary["alreadyHandled"] += alreadyHandled
    summary["notFound"] = sorted(set(summary.get("notFound", []) + notFound))

    fileEntry["status"] = "watching" if not freeUpdatesExpired(fileEntry) else "completed"
    fileEntry["lastCheckedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return createdTasks


registry = loadRegistry()

if not registry["files"]:
    print "<p>No files have been submitted yet. Run SubmitToNCOA.py from the Blue Toolbar first.</p>"
else:
    print "<table border=\"1\" cellpadding=\"4\"><tr><th>File</th><th>Submitted</th><th>Records</th><th>Result</th></tr>"

    for fileEntry in registry["files"]:
        fileName = fileEntry.get("fileName", "?")
        submittedDate = fileEntry.get("submittedDate", "")
        recordCount = fileEntry.get("recordCount", "")
        status = fileEntry.get("status")

        if status == "completed":
            summary = fileEntry.get("importSummary", {})
            print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Free update window closed ({3} flagged, " \
                  "{4} tasks created in total)</td></tr>".format(
                      fileName, submittedDate, recordCount, summary.get("flagged", 0), summary.get("createdTasks", 0))
            continue

        if status in ("cancelled", "errored"):
            print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>TrueNCOA reported this file {3}</td></tr>".format(
                fileName, submittedDate, recordCount, status)
            continue

        try:
            if status == "watching":
                if freeUpdatesExpired(fileEntry):
                    fileEntry["status"] = "completed"
                    summary = fileEntry.get("importSummary", {})
                    print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Free update window just closed " \
                          "({3} flagged, {4} tasks created in total)</td></tr>".format(
                              fileName, submittedDate, recordCount, summary.get("flagged", 0),
                              summary.get("createdTasks", 0))
                    continue

                triggerExport(fileEntry)

            elif status != "exporting":
                info = getFile(fileName)
                ncoaStatus = info.get("Status")

                if ncoaStatus in ("Cancelled", "Errored"):
                    fileEntry["status"] = ncoaStatus.lower()
                    print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>TrueNCOA reports this file {3}</td></tr>".format(
                        fileName, submittedDate, recordCount, ncoaStatus)
                    continue

                if ncoaStatus != "Processed":
                    print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Still {3} on TrueNCOA's side, check back later</td></tr>".format(
                        fileName, submittedDate, recordCount, ncoaStatus)
                    continue

                triggerExport(fileEntry)

            exportInfo = getFile(fileEntry["exportFileId"])
            exportStatus = exportInfo.get("Status")

            if exportStatus in ("Export", "Exporting"):
                print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Export still running on TrueNCOA's side, check back later</td></tr>".format(
                    fileName, submittedDate, recordCount)
                continue

            records = downloadRecords(fileEntry["exportFileId"])
            newTasksThisCheck = importRecords(fileEntry, records)
            summary = fileEntry["importSummary"]

            stillWatching = fileEntry["status"] == "watching"
            print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Checked: {3} new review task(s) this time " \
                  "({4} total). {5}</td></tr>".format(
                      fileName, submittedDate, recordCount, newTasksThisCheck, summary["createdTasks"],
                      "Still watching for new moves." if stillWatching else "Free update window now closed.")

        except Exception as ex:
            print "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>Error checking this file: {3}</td></tr>".format(
                fileName, submittedDate, recordCount, str(ex))

    print "</table>"

    saveRegistry(registry)
