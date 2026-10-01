#Roles=Admin

# Export for TrueDeceased
#
# Run this as a Python Script from the Blue Toolbar (the </> menu on any Search, Tag, or other people list) to
# build a CSV of the selected people for upload to TrueDeceased (https://truedeceased.com) for deceased
# suppression checks.
#
# TrueDeceased is a separate product/account from TrueNCOA, with its own web portal, and (as far as could be
# confirmed) isn't part of TrueNCOA's public API/CLI (https://github.com/truencoa/cli), so unlike
# SubmitToNCOA.py/CheckNCOAStatus.py this stays a manual export-and-upload step rather than a live API call.
#
# TrueDeceased matches on name, address, email, and/or phone number, so all of those are included below. Their
# portal lets you map your own column headers to their fields when you upload, so the header names below don't
# need to match their documentation exactly. The one column that matters is "PeopleId" -- set it up as a
# passthrough reference/keycode column so it's echoed back untouched in your results file.
# ImportDeceasedResults.py uses that column to match result rows back to the right person.

columns = [
    ("PeopleId", lambda p: p.PeopleId),
    ("FirstName", lambda p: p.FirstName),
    ("LastName", lambda p: p.LastName),
    ("AddressLine1", lambda p: p.PrimaryAddress),
    ("AddressLine2", lambda p: p.PrimaryAddress2),
    ("City", lambda p: p.PrimaryCity),
    ("State", lambda p: p.PrimaryState),
    ("Zip", lambda p: p.PrimaryZip),
    ("Email", lambda p: p.EmailAddress),
    ("CellPhone", lambda p: p.CellPhone),
    ("HomePhone", lambda p: p.Family.HomePhone if p.Family is not None else None),
]


def csvEscape(value):
    s = "" if value is None else unicode(value)
    if ',' in s or '"' in s or '\n' in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


model.Title = "Export for TrueDeceased"

count = q.BlueToolbarCount()

if count < 1:
    print "<p>Select a Search (or other people list) from the blue toolbar first, then run this report again.</p>"
else:
    headerRow = ",".join(csvEscape(name) for name, _ in columns)
    dataRows = []
    skipped = []

    for p in q.BlueToolbarReport():
        if not p.PrimaryAddress and not p.EmailAddress and not p.CellPhone:
            skipped.append(p)
            continue
        dataRows.append(",".join(csvEscape(getter(p)) for _, getter in columns))

    csvText = "\r\n".join([headerRow] + dataRows) + "\r\n"

    print "<p>{0} of {1} people have an address, email, or phone on file and are included below. " \
          "{2} were skipped for having none of those on file.</p>".format(len(dataRows), count, len(skipped))

    if skipped:
        print "<details><summary>People skipped (no address, email, or phone on file)</summary><ul>"
        for p in skipped:
            print "<li><a href=\"/Person2/{0}/\">{1}</a></li>".format(p.PeopleId, p.Name)
        print "</ul></details>"

    escapedCsv = csvText.replace("&", "&amp;").replace("<", "&lt;")

    print "<p><button id=\"deceased-download\">Download CSV for TrueDeceased</button></p>"
    print "<textarea readonly style=\"width:100%;height:300px;\" id=\"deceased-csv\">" + escapedCsv + "</textarea>"

    print """
    <script>
    document.getElementById('deceased-download').addEventListener('click', function () {
        var text = document.getElementById('deceased-csv').value;
        var blob = new Blob([text], {type: 'text/csv'});
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'touchpoint-deceased-export-' + new Date().toISOString().slice(0, 10) + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    });
    </script>
    """
