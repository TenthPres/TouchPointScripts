# Pckgd
# Title: Benevity Import
# Description: Imports Benevity disbursement reports as contributions from the granting foundation, soft-credited to the individual donors, with fees recorded as negative entries.
# Updates from: GitHub/TenthPres/TouchPointScripts/BenevityImport/BenevityImport.py
# Version: 0.1.0
# License: AGPL-3.0
# Author: James at Tenth

# noinspection PyUnresolvedReferences
from System import DateTime, Decimal
# noinspection PyUnresolvedReferences
from System.Globalization import CultureInfo

###########################################################################
# Configuration

# Only users with one of these roles may use this tool.
AllowedRoles = ['Admin', 'Finance']

# Map the "Disbursement From (Grantor)" column to the PeopleId of the business record that
# the gifts should be attributed to.  Rows from an unlisted grantor block the import.
GrantorPeopleIds = {
    "American Online Giving Foundation, Inc": 17363,  # TODO set PeopleId
}

# Map the "Project ID" column to a FundId.  Unlisted projects go to DefaultFundId.
FundIdsByProject = {}
DefaultFundId = 9  # TODO

# Soft credit for gifts where the donor didn't share their identity with Benevity.
AnonymousPeopleId = 999

# Gifts come from a nonprofit (the grantor), so they are not tax-deductible to Tenth's donors.
# 9 = Non-Tax-Deductible.
GiftContributionTypeId = 9

# Fees are recorded as a single negative entry per disbursement in this fund.
FeeFundId = 1  # TODO
# Contribution type for fee entries.  This must be set explicitly: TouchPoint would otherwise
# classify a negative amount as "Reversed" (7), which many reports exclude.
FeeContributionTypeId = 9

# Description of the Contribution Source applied to the bundles and contributions.
SourceDescription = "Other (Wire, etc)"

# Company matches are recorded as a separate entry from the same grantor.  Set to False to
# leave matches without a soft credit to the employee.
SoftCreditMatches = True

# Part of the Bundle Type description to use for new bundles.
BundleType = "Online"

# Person extra value used to remember manual donor matches for future imports.
DonorKeyExtraValue = "BenevityDonorKey"

# That's all the configuration.
###########################################################################

model.Transactional = True

NotShared = ["", "not shared by donor", "not available"]
Inv = CultureInfo.InvariantCulture


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def val(s):
    s = (s or "").strip()
    return "" if s.lower() in NotShared else s


def money(s):
    s = val(s)
    return Decimal.Parse(s, Inv) if s != "" else Decimal.Zero


def fmt(d):
    return d.ToString("0.00", Inv)


def date(s):
    # Only the date portion is used, so the UTC "Z" suffix doesn't shift days.
    return DateTime.ParseExact(s.strip()[:10], "yyyy-MM-dd", Inv)


def donorKey(r):
    if r['email'] != "":
        return r['email'].lower()
    if r['first'] != "" and r['last'] != "":
        return "{}|{}|{}".format(r['first'], r['last'], r['zip']).lower()
    return ""


def uniquePid(rows):
    pids = list(set([row.PeopleId for row in rows]))
    return pids[0] if len(pids) == 1 else 0


def findDonor(r):
    """Returns (PeopleId, how it was matched).  PeopleId is 0 when there is no confident match."""
    key = donorKey(r)
    if key == "":
        return AnonymousPeopleId, "Anonymous"

    living = "p.DeceasedDate IS NULL AND ISNULL(p.ArchivedFlag, 0) = 0"

    pid = uniquePid(q.QuerySql("""
        SELECT pe.PeopleId FROM PeopleExtra pe JOIN People p ON p.PeopleId = pe.PeopleId
        WHERE pe.Field = @field AND pe.Data = @key AND {}""".format(living),
        {'field': DonorKeyExtraValue, 'key': key}))
    if pid > 0:
        return pid, "Remembered"

    if r['email'] != "":
        pid = uniquePid(q.QuerySql("""
            SELECT p.PeopleId FROM People p
            WHERE (p.EmailAddress = @email OR p.EmailAddress2 = @email) AND {}""".format(living),
            {'email': r['email']}))
        if pid > 0:
            return pid, "Email"

    if r['first'] != "" and r['last'] != "" and r['zip'] != "":
        pid = uniquePid(q.QuerySql("""
            SELECT p.PeopleId FROM People p
            WHERE (p.FirstName = @first OR p.NickName = @first) AND p.LastName = @last
              AND LEFT(ISNULL(p.PrimaryZip, p.ZipCode), 5) = LEFT(@zip, 5) AND {}""".format(living),
            {'first': r['first'], 'last': r['last'], 'zip': r['zip']}))
        if pid > 0:
            return pid, "Name + Zip"

    return 0, "No match"


def parse(text):
    rows = []
    csv = model.CsvReader(text)
    while csv.Read():
        f = lambda name: csv.GetField(name) or ""
        r = {'disbursementId': f("Disbursement ID").strip(),
             'disbursementDate': date(f("Disbursement Date")),
             'grantor': f("Disbursement From (Grantor)").strip(),
             'company': val(f("Company Name")),
             'projectId': f("Project ID").strip(),
             'txId': f("Transaction ID").strip(),
             'donationDate': f("Donation Date").strip()[:10],
             'amount': money(f("Donation Amount")),
             'match': money(f("Match Amount")),
             'fees': money(f("Cause Support Fee")) + money(f("Merchant Fee")) + money(f("Check Fee")),
             'currency': f("Donation Currency").strip(), 'type': f("Donation Type").strip(),
             'first': val(f("Donor First Name")), 'last': val(f("Donor Last Name")),
             'email': val(f("Donor Email")),
             'zip': val(f("Donor Zip / Postal Code")),
             'comment': val(f("Donor Comment"))
             }
        r['grantorPid'] = GrantorPeopleIds.get(r['grantor'], 0)
        r['fundId'] = FundIdsByProject.get(r['projectId'], DefaultFundId)
        r['meta'] = "Benevity:" + r['txId']
        r['imported'] = model.FindContribution(metaInfo=r['meta']) is not None
        r['errors'] = []
        if r['grantorPid'] == 0:
            r['errors'].append("Unmapped grantor")
        if r['currency'] not in ["", "USD"]:
            r['errors'].append("Currency " + r['currency'])
        r['pid'], r['matchedBy'] = findDonor(r)
        rows.append(r)
    return rows


def sourceId():
    sid = q.QuerySqlInt("SELECT TOP 1 Id FROM lookup.ContributionSources WHERE Description = '{0}' OR code = '{0}'".format(
        SourceDescription.replace("'", "''")))
    if sid <= 0:
        raise Exception("Contribution Source '{}' not found.".format(SourceDescription))
    return sid


def addEntry(bh, r, amount, pid, desc, meta, softCreditPid=0, typeId=GiftContributionTypeId, fundId=None):
    fund = fundId or r['fundId']
    bd = model.AddContribution(r['disbursementDate'], fund, fmt(amount), r['txId'], desc[:256], pid, typeId)
    bd.Contribution.MetaInfo = meta[:100]
    bd.Contribution.ContributionSourceId = bh.SourceId
    if softCreditPid > 0:
        bd.Contribution.SoftCreditPeopleId = softCreditPid
    bh.BundleDetails.Add(bd)


def commit(rows):
    bundles = {}
    fees = {}
    source = sourceId()
    for r in rows:
        if r['imported'] or len(r['errors']) > 0:
            continue

        did = r['disbursementId']
        if did not in bundles:
            bundles[did] = model.FindOrCreateBundleHeader(r['disbursementDate'], BundleType, did)
            bundles[did].SourceId = source
        bh = bundles[did]

        # Manual overrides from the preview form take precedence, and are remembered.
        override = Data.GetValue("pid_" + r['txId'])
        if override is not None and str(override).strip().isdigit():
            r['pid'] = int(str(override).strip())
            key = donorKey(r)
            if r['pid'] > 0 and key != "" and r['matchedBy'] not in ["Remembered", "Email"]:
                model.AddExtraValueText("PeopleId = {}".format(r['pid']), DonorKeyExtraValue, key)

        userDesc = "Benevity ({} {})".format(r['company'] or r['grantor'], r['donationDate'])
        matchDesc = "Benevity ({} match {})".format(r['company'] or r['grantor'], r['donationDate'])

        if r['comment'].strip() != "":
            userDesc += " - " + r['comment'][:200]

        if r['amount'] != Decimal.Zero:
            addEntry(bh, r, r['amount'], r['grantorPid'], userDesc, r['meta'], r['pid'])
        if r['match'] != Decimal.Zero:
            addEntry(bh, r, r['match'], r['grantorPid'], matchDesc, r['meta'] + ":match",
                     r['pid'] if SoftCreditMatches else 0)

        if r['fees'] != Decimal.Zero:
            fees.setdefault(did, [r, Decimal.Zero])
            fees[did][1] += r['fees']

    for did, (r, total) in fees.items():
        meta = "Benevity fees:" + did
        if model.FindContribution(metaInfo=meta) is None:
            addEntry(bundles[did], r, Decimal.Negate(total), r['grantorPid'], "Benevity fees, disbursement " + did,
                     meta, 0, FeeContributionTypeId, FeeFundId)

    for bh in bundles.values():
        model.FinishBundle(bh)

    return bundles


def uploadForm():
    print """
<h2>Benevity Import</h2>
<p>In the Benevity Causes Portal, download the Disbursement Report CSV, then choose it here (or paste its contents).</p>
<form method="post" action="/PyScriptForm/""" + model.ScriptName + """">
    <input type="file" accept=".csv" onchange="var r = new FileReader(); r.onload = function() { document.getElementById('csv').value = r.result; }; r.readAsText(this.files[0]);" />
    <textarea id="csv" name="csv" rows="12" style="width:100%; font-family:monospace;"></textarea>
    <input type="hidden" name="step" value="preview" />
    <button type="submit" class="btn btn-primary">Preview</button>
</form>"""


def preview(rows):
    blocked = any(len(r['errors']) > 0 and not r['imported'] for r in rows)
    print "<h2>Benevity Import Preview</h2>"
    print "<p>Nothing has been saved yet.  Review donor matches below; enter a PeopleId to override or fill in a match.  Manual matches are remembered for future imports.</p>"
    print '<form method="post" action="/PyScriptForm/{}"><table'.format(model.ScriptName) + ' class="table table-condensed"><tr><th>Disbursement</th><th>Transaction</th><th>Donated</th><th>Amount</th><th>Match</th><th>Fees</th><th>Donor</th><th>Matched By</th><th>PeopleId</th><th>Comment</th><th>Status</th></tr>'
    for r in rows:
        name = esc((r['first'] + " " + r['last']).strip() or "(anonymous)")
        person = ""
        if r['pid'] > 0:
            person = ' &rarr; <a href="/Person2/{0}" target="_blank">{1}</a>'.format(r['pid'], esc(model.GetPerson(r['pid']).Name))
        status = "Already imported" if r['imported'] else (", ".join(r['errors']) or "Ready")
        pidInput = "" if r['imported'] else '<input name="pid_{}" value="{}" size="7" />'.format(esc(r['txId']), r['pid'] or "")
        print "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(r['disbursementId']), esc(r['txId']), esc(r['donationDate']), fmt(r['amount']), fmt(r['match']), fmt(r['fees']),
            name, person, r['matchedBy'], pidInput, esc(r['comment']), esc(status))
    print "</table>"
    print '<textarea name="csv" style="display:none;">{}</textarea>'.format(esc(Data.csv))
    print '<input type="hidden" name="step" value="commit" />'
    if blocked:
        print '<p class="text-danger">Some rows have errors (see Status).  Fix the configuration at the top of this script and preview again.</p>'
    else:
        print '<button type="submit" class="btn btn-primary">Import</button>'
    print "</form>"


userPerson = model.GetPerson(model.UserPeopleId)
if not any(userPerson.Users[0].InRole(role) for role in AllowedRoles):
    print "You do not have access to this tool."

elif model.HttpMethod == "post" and Data.step == "preview" and Data.csv != "":
    preview(parse(Data.csv))

elif model.HttpMethod == "post" and Data.step == "commit" and Data.csv != "":
    rows = parse(Data.csv)
    if any(len(r['errors']) > 0 and not r['imported'] for r in rows):
        print "Import blocked: some rows have errors.  Please preview again."
    else:
        bundles = commit(rows)
        print "<h2>Benevity Import Complete</h2><ul>"
        for did, bh in bundles.items():
            print '<li>Disbursement {0}: <a href="/Batches/Detail/{1}">bundle {1}</a> (left open for review)</li>'.format(esc(did), bh.BundleHeaderId)
        print "</ul>"
        if len(bundles) == 0:
            print "<p>Nothing new to import.</p>"

else:
    uploadForm()
