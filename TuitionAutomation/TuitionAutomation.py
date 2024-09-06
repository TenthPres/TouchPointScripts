from pprint import pprint
from datetime import datetime
from datetime import timedelta
import urllib

# model.TestEmail = True
model.Transactional = True


orgs = [
    {
        'id': 214,
        'name': "Kindergarten",
        'base': 885
    },

    {
        'id': 212,
        'name': "Pre-K",
        'base': 870
    },
    {
        'id': 213,
        'name': "Pre-K",
        'base': 870
    },

    {
        'id': 210,
        'name': "3-Year-Old",
        'base': 520
    },
    {
        'id': 211,
        'name': "3-Year-Old",
        'base': 520
    },

    {
        'id': 207,
        'name': "2-Year-Old",
        'base': 350
    },
    {
        'id': 209,
        'name': "2-Year-Old",
        'base': 350
    },
    {
        'id': 215,
        'name': "Afternoon - Mon",
        'base': 45,
        'payPer': "meeting",
        'discounts': False
    },
    {
        'id': 253,
        'name': "Afternoon - Thu",
        'base': 45,
        'payPer': "meeting",
        'discounts': False
    },
    # {
    #     'id': 244,
    #     'name': "Tuition Test Class",
    #     'base': 5
    # }
    ]

paymentOrgId = 51
minTransactionId = 28100
retroactive = True
now = datetime.now() - timedelta(days=9)

# #################  Basic configuration ends here. #########################

print "<a href=\"?view=assess\">Assess Next Due Amount</a><br />"
print "<a href=\"?view=emails\">Generate Email Previews</a><br />"
print "<a href=\"/RunScript/TuitionSummary/\">View Balances</a><br />"
print "<a href=\"/RunScript/TuitionProgramTotals/\">Program Totals</a><br />"

model.CurrentOrgId = paymentOrgId

# this is a container for collecting the "first child" of a given family, used to determine when a second child comes along.
firstChildren = {}
familyData = {}

showTuitionAssessment = not(Data.view.find("assess") == -1)
applyTuitionAssessment = not(Data.view.find("assessApply") == -1)
showEmails = not(Data.view.find("emails") == -1)
sendEmails = not(Data.view.find("sendemails") == -1)

model.Title = "Preschool Tuition Automation Tools"

monthToUse = now + timedelta(days=28)
monthToUseR = now

monthName = monthToUse.strftime('%B')
monthNameR = monthToUseR.strftime('%B')

retroactive = retroactive and monthNameR != 'Aug'

for cls in orgs:
    meetingCntSql = """SELECT COUNT(*) as mtgCnt FROM Meetings WHERE OrganizationId = {} AND YEAR(MeetingDate) = {} AND MONTH(MeetingDate) = {}""".format(cls['id'], monthToUse.year, monthToUse.month)
    meetingCnt = q.QuerySqlTop1(meetingCntSql).mtgCnt

    if showTuitionAssessment:
        print "<h2>{}</h2>".format(cls['name'])

        if cls.has_key('payPer') and cls['payPer'] == "meeting":
            print "<p><b>Tuition per Meeting - {} meetings in {}</b></p>".format(meetingCnt, monthName)
        else:
            print "<p><b>Tuition per Month</b></p>"

    for student in q.QueryList("MemberTypeCodes( Org={} ) = 220[Member]".format(cls['id'])):

        enrollmentDateSql = "SELECT EnrollmentDate FROM OrganizationMembers WHERE OrganizationId = {} AND PeopleId = {}".format(cls['id'], student.PeopleId)
        enrollmentDate = q.QuerySqlTop1(enrollmentDateSql).EnrollmentDate

        lastChargeSql = """SELECT MAX(TransactionDate) as date
            FROM [Transaction] t
                LEFT JOIN [TransactionPeople] tp ON t.OriginalId = tp.Id
                    WHERE t.OrgId = {} AND t.AdjustFee = 1 AND tp.PeopleId = {} AND Message LIKE '{}%'""".format(paymentOrgId, student.PeopleId, cls['name'])
        lastChargeDate = q.QuerySqlTop1(lastChargeSql)
        lastChargeDate = lastChargeDate if lastChargeDate is None else lastChargeDate.date

        isFirstChild = True
        if firstChildren.has_key("{}".format(student.FamilyId)):
            isFirstChild = (firstChildren["{}".format(student.FamilyId)].PeopleId == student.PeopleId)

        else:
            firstChildren["{}".format(student.FamilyId)] = student

        tuitionOverrideSql = """SELECT ome.IntValue as Tuition FROM OrgMemberExtra ome
        WHERE UPPER(ome.Field) = 'Tuition' AND ome.OrganizationId = {} AND ome.PeopleId = {}""".format(cls['id'], student.PeopleId)

        tuitionOverride = q.QuerySqlTop1(tuitionOverrideSql)

        meetingCntRSql = """SELECT COUNT(*) as mtgCnt FROM Meetings WHERE OrganizationId = {} AND YEAR(MeetingDate) = {} AND MONTH(MeetingDate) = {} AND MeetingDate > '{}'""".format(cls['id'], monthToUseR.year, monthToUseR.month, enrollmentDate)
        meetingCntR = q.QuerySqlTop1(meetingCntRSql).mtgCnt

        tuitionLine = cls['name']
        depositLine = cls['name'] + " Deposit"

        if tuitionOverride is None:

            tuitionCharge = 1.0 * cls['base']
            depositCharge = 1.0 * cls['base']
            tuitionChargeR = 1.0 * cls['base'] * (meetingCntR > 0)

            if cls.has_key('payPer') and cls['payPer'] == "meeting":
                tuitionCharge *= meetingCnt
                tuitionChargeR *= meetingCntR

            if cls.has_key('discounts') and cls['discounts'] == False:
                pass # no discounts
            else:
                if q.QueryCount("FamHasPrimAdultChurchMemb = 1[True] AND PeopleId = {}".format(student.PeopleId)) > 0:
                    tuitionCharge = tuitionCharge * (5.0/6.0)
                    tuitionChargeR = tuitionChargeR * (5.0/6.0)
                    tuitionLine = tuitionLine + " (Tenth Member Rate)"
                    # depositLine = depositLine + " (Tenth Member Rate)"  Do not apply discounts to Deposits.

                elif not isFirstChild:
                    tuitionCharge = tuitionCharge * (8.0/9.0)
                    tuitionChargeR = tuitionChargeR * (8.0/9.0)
                    tuitionLine = tuitionLine + " (Sibling Rate)"
                    # depositLine = depositLine + " (Sibling Rate)"  Do not apply discounts to Deposits.

        else:
            tuitionCharge = tuitionOverride.Tuition * 1.0
            tuitionChargeR = tuitionOverride.Tuition * 1.0
            depositCharge = tuitionOverride.Tuition * 1.0
            tuitionLine = tuitionLine + " (Special Rate)"
            depositLine = depositLine + " (Special Rate)"

            if cls.has_key('payPer') and cls['payPer'] == "meeting":
                tuitionCharge *= meetingCnt
                tuitionChargeR *= meetingCntR

        tuitionLineR = tuitionLine + " - " + monthNameR
        tuitionLine += " - " + monthName

        # Rounding, because the preschool wants that.
        tuitionCharge = round(tuitionCharge, 0)
        tuitionChargeR = round(tuitionChargeR, 0)
        depositCharge = round(depositCharge, 0)

        if enrollmentDate < lastChargeDate: # and not cls.has_key('payPer'):
            tuitionChargeR = 0.0

        if showTuitionAssessment:
            # print "<p>{} {} ${:,.2f} {}</p>".format(student.PreferredName, student.LastName, depositCharge, depositLine)
            if tuitionChargeR > 0 and retroactive:
                print "<p>{} {} ${:,.2f} {} (retro)</p>".format(student.PreferredName, student.LastName, tuitionChargeR, tuitionLineR)
            print "<p>{} {} ${:,.2f} {}</p>".format(student.PreferredName, student.LastName, tuitionCharge, tuitionLine)


        # Add to org, and add deposit if new to the org to account
        if not model.InOrg(student.PeopleId, paymentOrgId):
            model.JoinOrg(paymentOrgId, student.PeopleId)

            # Add deposit if needed
            if monthToUse.month > 6:
                model.AdjustFee(student.PeopleId, paymentOrgId, -depositCharge, depositLine)


        # TODO: Automatically add fee adjustments.
        # TODO: Calculate prorating of tuition.
        if applyTuitionAssessment:
            if tuitionChargeR > 0 and tuitionLineR != tuitionLine:
                model.AdjustFee(student.PeopleId, paymentOrgId, -tuitionChargeR, tuitionLineR)
            model.AdjustFee(student.PeopleId, paymentOrgId, -tuitionCharge, tuitionLine)


        # Initialize FamilyData dict for emails
        if not familyData.has_key("{}".format(student.FamilyId)):
            fd = {
                'recipients': [],
                'participants': [],
                'participantPids': [],
                'paylinks': [],
                'totalDue': 0.0,
                'print': '',
                'table': '',
                'hasBalanceDue': False,
                'otherParent': None
            }
        else:
            fd = familyData["{}".format(student.FamilyId)]

        needsToAppend = True
        for part in fd['participants']:
            if part.PeopleId == student.PeopleId:
                needsToAppend = False
                break

        if not needsToAppend:
            continue

        fd['participants'].append(student)
        fd['participantPids'].append(str(student.PeopleId))

        otherParent = model.ExtraValueInt(student.PeopleId, 'Parent')
        if otherParent != "":
            fd['otherParent'] = model.GetPerson(otherParent)


        transactionSql = """
            SELECT
            FORMAT(t.TransactionDate, 'MMM dd, yyyy') as Date,
            FORMAT(t.Amt * -1, 'C') as Amount,
            t.Amt as AmtNum,
            t.Name,
            t.Description

            FROM (

            -- Deposit
            SELECT
                t3.TransactionDate,
                tp3.Amt * 1.0 as Amt,
                COALESCE(REPLACE(t3.Message, 'APPROVED', 'Deposit'), 'Deposit') as Description,
                p3.Name
            FROM [TransactionPeople] tp3
                LEFT JOIN People p3 ON tp3.PeopleId = p3.PeopleId
                LEFT JOIN [Transaction] t3 ON tp3.Id = t3.Id
            WHERE tp3.Id IN (SELECT DISTINCT TranId FROM OrganizationMembers WHERE OrganizationId = {0} AND PeopleId IN ({1}))

            UNION

            -- Original Payment
            SELECT
                t2.TransactionDate,
                (tp2.Amt - t2.amtdue) * -1.0 as Amt,
                COALESCE(REPLACE(t2.Message, 'APPROVED', 'Online Transaction'), 'Discount Code') as Description,
                p2.Name
            FROM [TransactionPeople] tp2
                LEFT JOIN People p2 ON tp2.PeopleId = p2.PeopleId
                LEFT JOIN [Transaction] t2 ON tp2.Id = t2.Id
            WHERE t2.coupon is null AND tp2.Id IN (SELECT DISTINCT TranId FROM OrganizationMembers WHERE OrganizationId = {0} AND PeopleId IN ({1}))

            UNION

            -- Original Payment
            SELECT
                t4.TransactionDate,
                t4.Amt * -1.0 as Amt,
                COALESCE(REPLACE(t4.Message, 'APPROVED', 'Online Transaction'), 'Discount Code') as Description,
                p4.Name
            FROM [TransactionPeople] tp4
                LEFT JOIN People p4 ON tp4.PeopleId = p4.PeopleId
                LEFT JOIN [Transaction] t4 ON tp4.Id = t4.Id
            WHERE t4.coupon = 1 AND tp4.Id IN (SELECT DISTINCT TranId FROM OrganizationMembers WHERE OrganizationId = {0} AND PeopleId IN ({1}))

            UNION

            -- Adjustments
            SELECT
                t1.TransactionDate,
                t1.amt * -1.0 as Amt,
                REPLACE(t1.Message, 'APPROVED', 'Online Transaction') as Description,
                t1.Name
            FROM [Transaction] t1
            WHERE t1.Id <> t1.OriginalId AND t1.OriginalId IN (SELECT DISTINCT TranId FROM OrganizationMembers WHERE OrganizationId = {0} AND PeopleId IN ({1}))

            ) as t

            WHERE t.Amt <> 0

            ORDER BY t.TransactionDate, t.Description, t.Name
        """.format(paymentOrgId, ", ".join(fd['participantPids']))

        amtOwed = 0.0

        table = "<table style=\"width:100%;\"><thead><tr><th>Date</th><th>Amount</th><th>Person</th><th>Description</th></tr></thead><tbody>"
        for row in q.QuerySql(transactionSql):
            table = table + "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.Date, row.Amount, row.Name, row.Description)
            amtOwed += row.AmtNum or 0
        table += "</tbody></table>"

        table += "<p><b>Balance: ${:,.2f}</b></p><br />".format(amtOwed)

        fd['table'] = table
        amtOwed = amtOwed * 100

        if amtOwed > 0:
            fd['hasBalanceDue'] = True

        paylink = model.GetPayLink(student.PeopleId, paymentOrgId)
        if paylink is not None:
            paylink = paylink.replace(model.CmsHost, "")
            paylink = model.CmsHost + "/Logon?" + urllib.urlencode({"ReturnUrl": paylink})
            paylink = "<a href=\"{}\">paying online here</a>".format(paylink)

        if paylink not in fd['paylinks']:
            fd['paylinks'].append(paylink)

        fd['totalDue'] = amtOwed

        familyData["{}".format(student.FamilyId)] = fd

emailData = []
emailPids = []

if showTuitionAssessment:
    print "<p><a href=\"?view=assessApply\" onclick=\"return confirm('Are you sure?  This cannot be undone.');\">Apply all of these additional values to family balances</a></p>"


if showEmails:
    print "<p><a href=\"?view=sendemails&to=all\" onclick=\"return confirm('Are you sure?  This cannot be undone.');\">Send Emails to ALL families with balance</a></p>"


for fi in familyData:
    fam = familyData[fi]

    p1 = fam['participants'][0].Family.HeadOfHousehold or None
    p2 = fam['participants'][0].Family.HeadOfHouseholdSpouse or None
    p3 = fam['otherParent']

    if showEmails:

        if not sendEmails:
            print "<h2>{} Family</h2>".format(familyData[fi]['participants'][0].LastName)

        p1Name = None
        p2Name = None
        p3Name = None
        pPids = []
        if p1 is not None:
            p1Name = p1.Name
            pPids.append(p1.PeopleId)
        if p2 is not None:
            p2Name = p2.Name
            pPids.append(p2.PeopleId)
        if p3 is not None:
            p3Name = p3.Name
            pPids.append(p3.PeopleId)

        pPids = map(str, pPids)

        if not sendEmails:
            if familyData[fi]['hasBalanceDue']:
                print "<p><b>Sends to: {} {} {}</b>  <a href=\"?view=sendemails&to={}\">Send Individually</a></p>".format(p1Name, p2Name, p3Name, ",".join(pPids))
            else:
                print "<p><b>Does NOT Send to: {} {} {}</b>  <a href=\"?view=sendemails&to={}\">Send Individually</a></p>".format(p1Name, p2Name, p3Name, ",".join(pPids))

        # if len(familyData[fi]['participants']) > 1:
        familyData[fi]['print'] = familyData[fi]['table']

        amtOwed = familyData[fi]['totalDue']
        if amtOwed < 0:
            familyData[fi]['print'] += "<p>This credit of ${:,.2f} will be applied to future monthly billing cycles.  You do not need to do anything now.</p>".format(amtOwed * -0.01)
        elif amtOwed > 0:
            if paylink is None:
                familyData[fi]['print'] += "<h2 style=\"color: #ff0000\">Missing paylink for pid {}</h2>".format(student.PeopleId)
            familyData[fi]['print'] += "<p><b>Please make a payment of ${:,.2f} by sending in a check, or {}.</b></p>".format(amtOwed * 0.01, " AND ".join(familyData[fi]['paylinks']))
        else:
            familyData[fi]['print'] += "<p>Since there is no outstanding balance, you don't need to do anything.</p>".format(student.PreferredName)


        if not sendEmails:
            print familyData[fi]['print']

        if sendEmails and familyData[fi]['hasBalanceDue']:
            if p1 is not None:
                emailPids.append(p1.PeopleId)
                recipientData = model.DynamicData()
                recipientData.PeopleId = p1.PeopleId
                recipientData.Summary = familyData[fi]['print']
                emailData.append(recipientData)

            if p2 is not None:
                emailPids.append(p2.PeopleId)
                recipientData = model.DynamicData()
                recipientData.PeopleId = p2.PeopleId
                recipientData.Summary = familyData[fi]['print']
                emailData.append(recipientData)

            if p3 is not None:
                emailPids.append(p3.PeopleId)
                recipientData = model.DynamicData()
                recipientData.PeopleId = p3.PeopleId
                recipientData.Summary = familyData[fi]['print']
                emailData.append(recipientData)


if sendEmails:
    if Data.to == "all":
        emailPids = map(str, emailPids)
        emailPids = ",".join(emailPids)
    else:
        emailPids = Data.to

    print "<p>Emails have been sent to:</p>"

    print "PeopleIds = '{}'".format(emailPids)
    model.EmailContentWithPythonData("PeopleIds = '{}'".format(emailPids), 27796, "preschooltuition@tenth.org", "Tenth Preschool", "Preschool Tuition", emailData)

    if Data.to == "all":
        print """
        <script>
        alert("Emails sent");
        window.location.href = "?";
        </script>
        """

if applyTuitionAssessment:
    print """
    <script>
    alert("Assessments Applied");
    window.location.href = "?";
    </script>
    """