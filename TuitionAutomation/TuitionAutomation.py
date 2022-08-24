from pprint import pprint
from datetime import datetime
from datetime import timedelta
import urllib

print "<a href=\"?view=assess\">Assess Next Due Amount</a><br />"
print "<a href=\"?view=emails\">Generate Email Previews</a><br />"
print "<a href=\"/RunScript/TuitionSummary/\">View Balances</a><br />"
print "<a href=\"/RunScript/TuitionProgramTotals/\">Program Totals</a><br />"

paylinks = {
    "4932":"C7GDbkfC%2fQc%3d",
    "9452":"WxqBWPVAYqA%3d",
}

# model.TestEmail = True
model.Transactional = True


orgs = [
    {
        'id': 214,
        'name': "Kindergarten",
        'base': 837
    },
    
    {
        'id': 212,
        'name': "Pre-K",
        'base': 837
    },
    {
        'id': 213,
        'name': "Pre-K",
        'base': 837
    },
    
    {
        'id': 210,
        'name': "3-Year-Old",
        'base': 497
    },
    {
        'id': 211,
        'name': "3-Year-Old",
        'base': 497
    },
    
    {
        'id': 207,
        'name': "2-Year-Old",
        'base': 332
    },
    {
        'id': 209,
        'name': "2-Year-Old",
        'base': 332
    },
    {
        'id': 215,
        'name': "Afternoon - Mon",
        'base': 40,
        'payPer': "meeting",
        'discounts': False
    },
    {
        'id': 253,
        'name': "Afternoon - Thu",
        'base': 40,
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
minTransactionId = 17000
isDeposit = True

model.CurrentOrgId = paymentOrgId
    
# this is a container for collecting the "first child" of a given family, used to determine when a second child comes along.
firstChildren = {}
familyData = {}

showTuitionAssessment = not(Data.view.find("assess") == -1)
applyTuitionAssessment = not(Data.view.find("assessApply") == -1)
showEmails = not(Data.view.find("emails") == -1)
sendEmails = not(Data.view.find("sendemails") == -1)

model.Title = "Preschool Tuition Automation Tools"

monthToUse = datetime.now() + timedelta(days=28)

monthName = monthToUse.strftime('%B')


for cls in orgs:
    # TODO months properly
    meetingCntSql = """SELECT COUNT(*) as mtgCnt FROM Meetings WHERE OrganizationId = {} AND YEAR(MeetingDate) = {} AND MONTH(MeetingDate) = {}""".format(cls['id'], monthToUse.year, monthToUse.month)
    meetingCnt = q.QuerySqlTop1(meetingCntSql).mtgCnt
    
    if showTuitionAssessment:
        print "<h2>{}</h2>".format(cls['name'], meetingCnt)
        
        if cls.has_key('payPer') and cls['payPer'] == "meeting":
            print "<p><b>Tuition per Meeting - {} meetings</b></p>".format(meetingCnt)
        else:
            print "<p><b>Tuition per Month</b></p>"
    
    for student in q.QueryList("MemberTypeCodes( Org={} ) = 220[Member]".format(cls['id'])):
        
        isFirstChild = True
        if firstChildren.has_key("{}".format(student.FamilyId)):
            isFirstChild = (firstChildren["{}".format(student.FamilyId)].PeopleId == student.PeopleId)
            
        else:
            firstChildren["{}".format(student.FamilyId)] = student
        
        tuitionOverrideSql = """SELECT ome.IntValue as Tuition FROM OrgMemberExtra ome 
        WHERE UPPER(ome.Field) = 'Tuition' AND ome.OrganizationId = {} AND ome.PeopleId = {}""".format(cls['id'], student.PeopleId)
        
        tuitionOverride = q.QuerySqlTop1(tuitionOverrideSql)
        
        tuitionLine = cls['name']
        depositLine = cls['name'] + " Deposit"
        
        if tuitionOverride is None:
            
            tuitionCharge = 1.0 * cls['base']
            depositCharge = 1.0 * cls['base']
            
            if cls.has_key('payPer') and cls['payPer'] == "meeting":
                tuitionCharge *= meetingCnt
            
            if cls.has_key('discounts') and cls['discounts'] == False:
                pass # no discounts
            else:
                if not isDeposit and q.QueryCount("FamHasPrimAdultChurchMemb = 1[True] AND PeopleId = {}".format(student.PeopleId)) > 0:
                    tuitionCharge = tuitionCharge * (5.0/6.0)
                    tuitionLine = tuitionLine + " (Tenth Member Rate)"
                    depositLine = depositLine + " (Tenth Member Rate)"
                
                elif not isDeposit and not isFirstChild:
                    tuitionCharge = tuitionCharge * (8.0/9.0)
                    tuitionLine = tuitionLine + " (Sibling Rate)"
                    depositLine = depositLine + " (Sibling Rate)"
        
        else: 
            tuitionCharge = tuitionOverride.Tuition * 1.0
            depositCharge = tuitionOverride.Tuition * 1.0
            tuitionLine = tuitionLine + " (Special Rate)"
            depositLine = depositLine + " (Special Rate)"
            
            if cls.has_key('payPer') and cls['payPer'] == "meeting":
                tuitionCharge *= meetingCnt
            
        tuitionLine += " - " + monthName
        
        if showTuitionAssessment:
            if isDeposit:
                print "<p>{} {} ${:,.2f} {}</p>".format(student.PreferredName, student.LastName, depositCharge, depositLine)
            else:
                print "<p>{} {} ${:,.2f} {}</p>".format(student.PreferredName, student.LastName, tuitionCharge, tuitionLine)
        
        
        # Add to org, and add deposit if new to the org to account
        if not model.InOrg(student.PeopleId, paymentOrgId):
            model.JoinOrg(paymentOrgId, student.PeopleId)
            if monthToUse.month > 6:
                model.AdjustFee(student.PeopleId, paymentOrgId, -depositCharge, depositLine)
        
        
        # TODO: Automatically add fee adjustments.
        # TODO: Calculate proration of tuition. 
        if applyTuitionAssessment and not isDeposit:
            model.AdjustFee(student.PeopleId, paymentOrgId, -tuitionCharge, tuitionLine)
        
        
        # Initialize FamilyData dict for emails
        if not familyData.has_key("{}".format(student.FamilyId)):
            fd = {
                'recipients': [],
                'participants': [],
                'print': '',
                'hasBalanceDue': False
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
        
        fd['print'] += "<h3>Tuition for {}</h3>".format(student.PreferredName)
        
        transactionSql = """
        SELECT 
            FORMAT(t.TransactionDate, 'MMM dd, yyyy') as Date,
            FORMAT(t.Amt * -1, 'C') as Amount,
            REPLACE(t.Message, 'APPROVED', 'Online Transaction') as Description
        FROM [Transaction] t
        LEFT JOIN [TransactionPeople] tp ON t.OriginalId = tp.Id
        WHERE t.OrgId = {0} AND tp.PeopleId = {1} AND t.Approved = 1 AND t.id > {2}
        """.format(paymentOrgId, student.PeopleId, minTransactionId)
        
        totalSql = """
        SELECT SUM(t.Amt) * -100 as Amount
        FROM [Transaction] t
        LEFT JOIN [TransactionPeople] tp ON t.OriginalId = tp.Id
        WHERE t.OrgId = {} AND tp.PeopleId = {} AND t.Approved = 1 AND t.id > {}
        """.format(paymentOrgId, student.PeopleId, minTransactionId)
        
        amtOwed = q.QuerySqlInt(totalSql)
        
        table = "<table style=\"width:100%;\"><thead><tr><th>Date</th><th>Amount</th><th>Description</th></tr></thead><tbody>"
        for row in q.QuerySql(transactionSql):
            table = table + "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(row.Date, row.Amount, row.Description)
        table += "</tbody></table>"
        
        table += "<p><b>Balance: ${:,.2f}</b></p><br />".format(amtOwed * 0.01)
        
        fd['print'] += table
        if amtOwed > 0:
            fd['hasBalanceDue'] = True
        
        # print model.EmailStr("{paylinkurl}", student.PeopleId) TODO make this work
        
        pid_str = "{}".format(student.PeopleId)
        if not paylinks.has_key(pid_str):
            paylink = None
        else:
            paylink = "/OnlineReg/PayAmtDue?q=" + paylinks[pid_str]
            paylink = "https://my.tenth.org/Logon?" + urllib.urlencode({"ReturnUrl": paylink})
        
        if amtOwed < 0:
            fd['print'] += "<p>This credit of ${:,.2f} will be applied to future monthly billing cycles.  You do not need to do anything now.</p>".format(amtOwed * -0.01)
        elif amtOwed > 0:
            if paylink is None:
                fd['print'] += "<h2 style=\"color: #ff0000\">Missing paylink for pid {}</h2>".format(student.PeopleId)
            fd['print'] += "<p><b>Please make a payment of ${:,.2f} for {} by sending in a check, or <a href=\"{}\">paying online here</a>.</b></p>".format(amtOwed * 0.01, student.PreferredName, paylink)
        else:
            fd['print'] += "<p>Since there is no outstanding balance, you don't need to do anything.</p>".format(student.PreferredName)
        
        fd['print'] += "<br />"
        
        familyData["{}".format(student.FamilyId)] = fd
        
emailData = []
emailPids = []
        
for fi in familyData:
    fam = familyData[fi]
    
    p1 = fam['participants'][0].Family.HeadOfHousehold or None
    p2 = fam['participants'][0].Family.HeadOfHouseholdSpouse or None
    
    if showEmails:
        
        if not sendEmails:
            print "<h2>{} Family</h2>".format(familyData[fi]['participants'][0].LastName)
        
        p1Name = None
        p2Name = None
        pPids = []
        if p1 is not None:
            p1Name = p1.Name
            pPids.append(p1.PeopleId)
        if p2 is not None:
            p2Name = p2.Name
            pPids.append(p2.PeopleId)
            
        pPids = map(str, pPids)
        
        if not sendEmails:
            if familyData[fi]['hasBalanceDue']:
                print "<p><b>Sends to: {} {}</b>  <a href=\"?view=sendemails&to={}\">Send Individually</a></p>".format(p1Name, p2Name, ",".join(pPids))
            else:
                print "<p><b>Does NOT Send to: {} {}</b>  <a href=\"?view=sendemails&to={}\">Send Individually</a></p>".format(p1Name, p2Name, ",".join(pPids))
        
        if len(familyData[fi]['participants']) > 1:
            familyData[fi]['print'] = "<p>Each child's balance and payments are listed below.  Please note that each child's account must be payed separately if paying online.</p><br />" + familyData[fi]['print']
        
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
                

if sendEmails:
    if Data.to == "all":
        emailPids = map(str, emailPids)
        emailPids = ",".join(emailPids)
    else:
        emailPids = Data.to
        
    print "<p>Emails have been sent to:</p>"
        
    print "PeopleIds = '{}'".format(emailPids)
    model.EmailContentWithPythonData("PeopleIds = '{}'".format(emailPids), 27796, "preschool@tenth.org", "Tenth Preschool", "Preschool Tuition", emailData)
