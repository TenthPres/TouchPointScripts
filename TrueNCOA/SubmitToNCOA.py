#Roles=Admin

# Submit People to TrueNCOA for a National Change of Address (NCOA) Check
#
# Run this as a Python Script from the Blue Toolbar (the </> menu) against any Search or other people list. It
# submits the selected people to TrueNCOA (https://truencoa.com) using the same HTTP API their own CLI tool uses
# -- see https://github.com/truencoa/cli (Program.cs) for the reference implementation this script is based on,
# since TrueNCOA's account-specific Postman/API docs weren't reachable while writing this. Concretely, it:
#   1. Creates a file on TrueNCOA and uploads each selected person as a record
#      (POST files/{fileName}/records)
#   2. Marks that file "submitted" so TrueNCOA starts NCOA processing against it
#      (PATCH files/{fileName}?status=submit)
#
# NCOA processing takes a while and happens on TrueNCOA's side, so this script doesn't wait around for it. It
# saves what it submitted to a small tracking file (see registryContentName below) so CheckNCOAStatus.py knows
# what to check on later, and can pick up the rest of the process (export, download, and creating review Tasks)
# whenever you run it.
#
# TrueDeceased (https://truedeceased.com) is a related but separate product with its own account/portal, and
# doesn't appear to be part of TrueNCOA's API/CLI, so it isn't handled by this script. See
# ExportForDeceasedCheck.py / ImportDeceasedResults.py for that, as a manual upload/download instead.

import json
import time
import urllib
from datetime import datetime

# ##################### #
# Configuration -- see https://truencoa.com for account setup
# ##################### #

trueNcoaUserName = "YOUR TRUENCOA ACCOUNT EMAIL"
trueNcoaPassword = "YOUR TRUENCOA PASSWORD"

# Use https://api.testing.truencoa.com/ while testing, https://api.truencoa.com/ for real submissions.
trueNcoaBaseUrl = "https://api.truencoa.com/"

# Optional. Only needed if your TrueNCOA account uses more than one "mailer" and this submission needs to go to
# a specific one (the CLI derives this from a "[mailer_name]" tag in the input filename). Leave blank otherwise.
trueNcoaMailer = ""

# How many people to include in a single upload request. TrueNCOA's own CLI batches every 10,000 records --
# there's no reason a single church's list needs anywhere near that, so this is turned down.
batchSize = 500

# Where the list of files we've submitted (and how far along each one is) gets tracked, as a Special Content
# text document, so CheckNCOAStatus.py knows what to check on.
registryContentName = "TrueNCOA-Files.json"

# NOTE: model.RestPatch is used below for the HTTP PATCH calls TrueNCOA's API requires. This repo hasn't needed
# a PATCH call anywhere else, so it's not confirmed that TouchPoint's Python Script API actually exposes a
# method by that name. If this script errors out on that line, check TouchPoint's Python Script API reference
# (or ask TouchPoint support) for the right way to send an HTTP PATCH request, and swap it in here and in
# CheckNCOAStatus.py.

# All done configuring. On to the code.
############################################################################################

recordFields = [
    "individual_id",
    "individual_first_name",
    "individual_last_name",
    "address_line_1",
    "address_line_2",
    "address_city_name",
    "address_state_code",
    "address_postal_code",
]


def personToValues(p):
    return [p.PeopleId, p.FirstName, p.LastName, p.PrimaryAddress, p.PrimaryAddress2, p.PrimaryCity,
            p.PrimaryState, p.PrimaryZip]


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


model.Title = "Submit People to TrueNCOA"

count = q.BlueToolbarCount()

if count < 1:
    print "<p>Select a Search (or other people list) from the blue toolbar first, then run this report again.</p>"
elif trueNcoaUserName.startswith("YOUR ") or trueNcoaPassword.startswith("YOUR "):
    print "<p>Set trueNcoaUserName and trueNcoaPassword at the top of this script before running it.</p>"
else:
    included = []
    skipped = []

    for p in q.BlueToolbarReport():
        if not p.PrimaryAddress:
            skipped.append(p)
        else:
            included.append(p)

    if len(included) < 1:
        print "<p>None of the {0} selected people have a mailing address on file. Nothing to submit.</p>".format(count)
    else:
        fileName = "TouchPoint_{0}".format(int(time.time()))

        recordsUrl = "{0}files/{1}/records".format(trueNcoaBaseUrl, fileName)
        if trueNcoaMailer:
            recordsUrl += "?mailer=" + urllib.quote(trueNcoaMailer)

        uploadError = None
        i = 0
        while i < len(included) and uploadError is None:
            batch = included[i:i + batchSize]
            pairs = []
            for p in batch:
                values = personToValues(p)
                for fieldName, value in zip(recordFields, values):
                    pairs.append((fieldName, "" if value is None else unicode(value)))

            body = urllib.urlencode(pairs)
            headers = authHeaders({"Content-Type": "application/x-www-form-urlencoded"})

            try:
                model.RestPost(recordsUrl, headers, body)
            except Exception as ex:
                uploadError = str(ex)

            i += batchSize

        if uploadError is not None:
            print "<p>Uploading records to TrueNCOA failed: {0}</p>".format(uploadError)
            print "<p>File <code>{0}</code> may be partially uploaded on TrueNCOA's side. " \
                  "You may want to check/cancel it there before trying again.</p>".format(fileName)
        else:
            submitUrl = "{0}files/{1}?status=submit".format(trueNcoaBaseUrl, fileName)

            try:
                model.RestPatch(submitUrl, authHeaders(), "")

                registry = loadRegistry()
                registry["files"].append({
                    "fileName": fileName,
                    "submittedDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "submittedBy": model.UserPeopleId,
                    "recordCount": len(included),
                    "peopleIds": [p.PeopleId for p in included],
                    "status": "submitted",
                })
                saveRegistry(registry)

                print "<p>Submitted {0} of {1} selected people to TrueNCOA as file <code>{2}</code>.</p>".format(
                    len(included), count, fileName)
                print "<p>NCOA processing happens on TrueNCOA's side and isn't instant. Run " \
                      "<b>CheckNCOAStatus.py</b> later (e.g. tomorrow) to check progress, export, download the " \
                      "results, and create review Tasks for anyone flagged as having moved.</p>"
            except Exception as ex:
                print "<p>Records uploaded, but marking the file \"submit\"ted failed: {0}</p>".format(str(ex))
                print "<p>File <code>{0}</code> has your records but TrueNCOA may not start processing it until " \
                      "that step succeeds. Check the file's status on TrueNCOA, or try again.</p>".format(fileName)

        if skipped:
            print "<details><summary>{0} people skipped (no address on file)</summary><ul>".format(len(skipped))
            for p in skipped:
                print "<li><a href=\"/Person2/{0}/\">{1}</a></li>".format(p.PeopleId, p.Name)
            print "</ul></details>"
