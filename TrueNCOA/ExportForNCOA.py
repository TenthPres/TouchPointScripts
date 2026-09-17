#Roles=Admin

# Export for TrueNCOA / TrueDeceased
#
# Run this as a Python Script from the Blue Toolbar (the </> menu on any Search, Tag, or other people list) to
# build a CSV of the selected people, formatted for upload to:
#   - TrueNCOA (https://truencoa.com) for National Change of Address (NCOA) processing
#   - TrueDeceased (https://truedeceased.com) for deceased suppression
#
# Both services let you map your own column headers to their fields when you upload through their web portal, so
# the header names below don't need to match their documentation exactly. The one column that matters is
# "PeopleId" -- when you set up your account/upload, tell TrueNCOA/TrueDeceased to treat it as a passthrough
# reference/keycode column so it's echoed back untouched in your results file. ImportNCOAResults.py and
# ImportDeceasedResults.py use that column to match result rows back to the right person.
#
# If you instead automate the upload through TrueNCOA's CLI or REST API, check their current Input File Guide
# (available from your TrueNCOA account) for the exact header names/order they expect, and adjust the `columns`
# list below to match.

columns = [
    ("PeopleId", lambda p: p.PeopleId),
    ("FirstName", lambda p: p.FirstName),
    ("LastName", lambda p: p.LastName),
    ("AddressLine1", lambda p: p.PrimaryAddress),
    ("AddressLine2", lambda p: p.PrimaryAddress2),
    ("City", lambda p: p.PrimaryCity),
    ("State", lambda p: p.PrimaryState),
    ("Zip", lambda p: p.PrimaryZip),
]


def csvEscape(value):
    s = "" if value is None else unicode(value)
    if ',' in s or '"' in s or '\n' in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


model.Title = "Export for NCOA / Deceased Check"

count = q.BlueToolbarCount()

if count < 1:
    print "<p>Select a Search (or other people list) from the blue toolbar first, then run this report again.</p>"
else:
    headerRow = ",".join(csvEscape(name) for name, _ in columns)
    dataRows = []
    skipped = []

    for p in q.BlueToolbarReport():
        if not p.PrimaryAddress:
            skipped.append(p)
            continue
        dataRows.append(",".join(csvEscape(getter(p)) for _, getter in columns))

    csvText = "\r\n".join([headerRow] + dataRows) + "\r\n"

    print "<p>{0} of {1} people have a mailing address on file and are included below. " \
          "{2} were skipped for having no address on file.</p>".format(len(dataRows), count, len(skipped))

    if skipped:
        print "<details><summary>People skipped (no address on file)</summary><ul>"
        for p in skipped:
            print "<li><a href=\"/Person2/{0}/\">{1}</a></li>".format(p.PeopleId, p.Name)
        print "</ul></details>"

    escapedCsv = csvText.replace("&", "&amp;").replace("<", "&lt;")

    print "<p><button id=\"ncoa-download\">Download CSV for TrueNCOA / TrueDeceased</button></p>"
    print "<textarea readonly style=\"width:100%;height:300px;\" id=\"ncoa-csv\">" + escapedCsv + "</textarea>"

    print """
    <script>
    document.getElementById('ncoa-download').addEventListener('click', function () {
        var text = document.getElementById('ncoa-csv').value;
        var blob = new Blob([text], {type: 'text/csv'});
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'touchpoint-ncoa-export-' + new Date().toISOString().slice(0, 10) + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    });
    </script>
    """
