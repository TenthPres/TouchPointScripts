import clr
from System import DateTime, String, Convert
from System.Text.RegularExpressions import Regex, RegexOptions
from pprint import pprint

global q, model

checkCode = "ComboPS"
employeeOrgId = 61
stateCode = "PA"

people_needing_checks = '''
    IsProspectOf( Org={0} ) = 1[True]
    OR IsMemberOf( Org={0} ) = 1[True]
    OR MemberTypeCodes( Div=19[Children's Bible School] ) IN ( {1} )
    OR PmmBackgroundCheckStatus(  ) IN ( '0,Error', '1,Not Submitted', '2,Submitted', '3,Complete' )
'''.format(employeeOrgId, ','.join(map(str, q.QuerySqlInts(
    '''SELECT mt.Id FROM lookup.MemberType AS mt WHERE mt.AttendanceTypeId = 10'''))))  # TODO replace hard-coded values with generic versions


class BackgroundChecker:
    Statuses = {
        'NOT_RUN': 0,
        'CHECK_STARTED': 1,
        'CHECK_COMPLETE': 2,
        'REVIEW_COMPLETE': 4,
        'PASSED': 8
    }
    Expirations = {
        'basic': DateTime.Now.AddMonths(-12),
        'paVol': DateTime.Now.AddMonths(-60),
        'paEmp': DateTime.Now.AddMonths(-60),
        'affid': DateTime.Now.AddMonths(-60),
        'fingr': DateTime.Now.AddMonths(-60),
        'isMin': DateTime.Now.AddMonths(-216)
    }
    Renewals = {
        'basic': DateTime.Now.AddMonths(-11),
        'paVol': DateTime.Now.AddMonths(-57),
        'paEmp': DateTime.Now.AddMonths(-57),
        'affid': DateTime.Now.AddMonths(-57),
        'fingr': DateTime.Now.AddMonths(-57),
        'isMin': DateTime.Now.AddMonths(-213)
    }

    def __init__(self, pid=model.UserPeopleId):
        self.person = model.GetPerson(pid)
        self.statusSet = False
        self.statusCur = {  # Current status
            'basic': 0,
            'paVol': 0,
            'paEmp': 0,
            'affid': 0,
            'fingr': 0,
            'isMin': 0
        }
        self.statusExp = {  # Status if items needing renewal are allowed to expire.
            'basic': 0,
            'paVol': 0,
            'paEmp': 0,
            'affid': 0,
            'fingr': 0,
            'isMin': 0
        }
        self.statusHis = {  # Historical Status (effectively, collection of all checks)
            'basic': 0,
            'paVol': 0,
            'paEmp': 0,
            'affid': 0,
            'fingr': 0,
            'isMin': 0
        }

    def items_needed(self, for_employment):
        self.determine_status()
        for_employment = not not for_employment
        items = []
        eligibleForSubmission = True

        # get minors out of the way
        if not for_employment and (self.statusExp['isMin'] & 8 == 8):
            return items  # if the subject is a minor not looking for employment, they need nothing.

        # Bio: Full Name, Email, etc.
        if (
                String.IsNullOrEmpty(self.person.FirstName) or
                String.IsNullOrEmpty(self.person.LastName) or
                (self.person.GenderId != 1 and self.person.GenderId != 2) or
                self.person.BirthYear < 1900  # meant to detect if null
        ) and (
                (for_employment and self.statusExp['paEmp'] & 8 == 0) or
                self.statusExp['paVol'] & 8 == 0 or
                self.statusExp['basic'] & 8 == 0):
            items.append('Bio')
            eligibleForSubmission = False

        # SSN
        if String.IsNullOrEmpty(self.person.Ssn) and (
                (for_employment and self.statusExp['paEmp'] & 8 == 0) or
                self.statusExp['paVol'] & 8 == 0 or
                self.statusExp['basic'] & 8 == 0):
            items.append('Ssn')
            eligibleForSubmission = False

        # PMM Submission
        if eligibleForSubmission and for_employment and self.statusExp['paEmp'] & 1 == 0:
            items.append("submit_emp")
        elif eligibleForSubmission and self.statusExp['paVol'] & 1 == 0:
            items.append("submit_vol")
        elif eligibleForSubmission and self.statusExp['basic'] & 1 == 0:
            items.append("submit_basic")

        # PMM Completion Actions
        if for_employment and self.statusExp['paEmp'] & 1 == 1 and self.statusExp['paEmp'] & 2 == 0:
            items.append("receive_emp")
        elif self.statusExp['paVol'] & 1 == 1 and self.statusExp['paVol'] & 2 == 0:
            items.append("receive_vol")
        elif self.statusExp['basic'] & 1 == 1 and self.statusExp['basic'] & 2 == 0:
            items.append("receive_basic")

        # PMM Review Actions
        if for_employment and self.statusExp['paEmp'] & 2 == 2 and self.statusExp['paEmp'] & 4 == 0:
            items.append("review_emp")
        elif self.statusExp['paVol'] & 2 == 2 and self.statusExp['paVol'] & 4 == 0:
            items.append("review_vol")
        elif self.statusExp['basic'] & 2 == 2 and self.statusExp['basic'] & 4 == 0:
            items.append("review_bas")

        # FBI or Affidavit Submission
        if for_employment and self.statusExp['fingr'] & 2 == 0:
            items.append("submit_fbi")
        elif not for_employment and self.statusExp['fingr'] & 2 == 0 and self.statusExp['affid'] & 2 == 0:
            items.append("submit_fbi_aff")

        # FBI or Affid Approval TODO

        return items

    def can_employ(self):
        self.determine_status()
        return (self.status_employ() & 15) == 15

    def status_employ(self):
        self.determine_status()
        return self.statusCur['basic'] & self.statusCur['paEmp'] & self.statusCur['fingr']

    def can_volunteer(self):
        self.determine_status()
        return (self.status_volunteer() & 15) == 15

    def status_volunteer(self):
        self.determine_status()
        return (self.statusCur['basic'] & self.statusCur['paVol'] &
                (self.statusCur['affid'] | self.statusCur['fingr'])) | \
               self.statusCur['isMin']

    def determine_status(self):
        if self.statusSet:
            return

        # PMM CHECKS
        checks_sql = "SELECT TOP 20 * FROM [BackgroundChecks] WHERE [PeopleId] = @p1 AND DATEDIFF(DAY, DATEADD(YEAR, -10, GETDATE()), [Updated]) > 0 ORDER BY [Updated] DESC".format(
            self.person.PeopleId)
        for check in q.QuerySql(checks_sql, self.person.PeopleId):
            check_status = 0

            if check.StatusID >= 2:  # Check has begun
                check_status = check_status | self.Statuses['CHECK_STARTED']

                if check.StatusID == 3:  # Check is complete
                    check_status = check_status | self.Statuses['CHECK_COMPLETE']

                    if check.IssueCount == 0:
                        check_status = check_status | self.Statuses['REVIEW_COMPLETE'] | self.Statuses['PASSED']
                    else:
                        check_status = check_status | self.Statuses['REVIEW_COMPLETE']
                        # TODO: Can this pass if there are issues?

            if check.ServiceCode == "ComboPS" and check.ReportLabelID == 1:
                # PA Employee

                self.statusHis['paEmp'] = self.statusHis['paEmp'] | check_status

                if DateTime.Compare(check.Updated, self.Renewals['paEmp']) > 0:
                    self.statusExp['paEmp'] = self.statusExp['paEmp'] | check_status

                if DateTime.Compare(check.Updated, self.Expirations['paEmp']) > 0:
                    self.statusCur['paEmp'] = self.statusCur['paEmp'] | check_status

            if check.ServiceCode == "ComboPS":
                # PA Volunteer

                self.statusHis['paVol'] = self.statusHis['paVol'] | check_status

                if DateTime.Compare(check.Updated, self.Renewals['paVol']) > 0:
                    self.statusExp['paVol'] = self.statusExp['paVol'] | check_status

                if DateTime.Compare(check.Updated, self.Expirations['paVol']) > 0:
                    self.statusCur['paVol'] = self.statusCur['paVol'] | check_status

            if check.ServiceCode == "Combo" or check.ServiceCode == "ComboPS":
                # Basic

                self.statusHis['basic'] = self.statusHis['basic'] | check_status

                if DateTime.Compare(check.Updated, self.Renewals['basic']) > 0:
                    self.statusExp['basic'] = self.statusExp['basic'] | check_status

                if DateTime.Compare(check.Updated, self.Expirations['basic']) > 0:
                    self.statusCur['basic'] = self.statusCur['basic'] | check_status

        # MINOR'S WAIVER
        if self.person.BirthDate > self.Expirations['isMin']:
            self.statusCur['isMin'] = self.Statuses['CHECK_STARTED'] | self.Statuses['CHECK_COMPLETE'] | \
                                      self.Statuses['REVIEW_COMPLETE'] | self.Statuses['PASSED']
        if self.person.BirthDate > self.Renewals['isMin']:
            self.statusExp['isMin'] = self.Statuses['CHECK_STARTED'] | self.Statuses['CHECK_COMPLETE'] | \
                                      self.Statuses['REVIEW_COMPLETE'] | self.Statuses['PASSED']

        # FBI Fingerprinting
        for doc in self.person.VolunteerForms:
            rx = Regex("(?<docType>\w+)\s+(?<date>[0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",
                       RegexOptions.Compiled | RegexOptions.IgnoreCase);
            rm = rx.Match(doc.Name)

            if not rm.Success:
                continue

            if rm.Groups['docType'].Value.ToLower() == "fbi":
                dt = Convert.ToDateTime(rm.Groups['date'].Value)

                # TODO impose some form of verification here.
                check_status = self.Statuses['CHECK_STARTED'] | self.Statuses['CHECK_COMPLETE'] | \
                               self.Statuses['REVIEW_COMPLETE'] | self.Statuses['PASSED']

                self.statusHis['fingr'] = self.statusHis['fingr'] | check_status

                if DateTime.Compare(dt, self.Renewals['fingr']) > 0:
                    self.statusExp['fingr'] = self.statusExp['fingr'] | check_status

                if DateTime.Compare(dt, self.Expirations['fingr']) > 0:
                    self.statusCur['fingr'] = self.statusCur['fingr'] | check_status

        self.statusSet = True


# DETERMINE WHAT TO SHOW

userPerson = model.GetPerson(model.UserPeopleId)

if model.Data.view == "list" and userPerson.Users[0].InRole('Admin'):

    model.Styles = "<style>.y { background: #dfd;} .n { background: #fdd; }</style>"


    def status_to_cell(status, mask):
        return "<td class=\"{}\">{}</td>".format(("y" if status & mask == mask else "n"),
                                                 ("Yes" if status & mask == mask else "No"))


    def status_to_row(status):
        r = ""
        r += status_to_cell(status, 1)
        r += status_to_cell(status, 2)
        r += status_to_cell(status, 4)
        r += status_to_cell(status, 8)
        return r


    print "<table style=\"width:100%;\">"
    for p in q.QueryList(people_needing_checks):
        bgc = BackgroundChecker(p.PeopleId)
        print "<tr>"
        print "<th colspan=2>{} {}</th>".format(bgc.person.PreferredName, bgc.person.LastName)
        print "<td colspan=2>{}</td>".format("Employable" if bgc.can_employ() else "Not Employable")
        print "<td colspan=2>{}</td>".format("Volunteer" if bgc.can_volunteer() else "No Volunteering")
        print "</tr>"

        print "<tr><td colspan=2>Current</td><td>Started</td><td>Complete</td><td>Reviewed</td><td>Passed</td></tr>"

        for ci in bgc.statusCur:
            print "<tr>"
            print "<td>&nbsp;&nbsp;&nbsp;</td><td>{}</td>".format(ci)
            print status_to_row(bgc.statusCur[ci])
            print "</tr>"

        print "<tr><td colspan=2>Expiring</td><td>Started</td><td>Complete</td><td>Reviewed</td><td>Passed</td></tr>"

        for ci in bgc.statusExp:
            print "<tr>"
            print "<td>&nbsp;&nbsp;&nbsp;</td><td>{}</td>".format(ci)
            print status_to_row(bgc.statusExp[ci])
            print "</tr>"

        print "<tr><td colspan=2>Historical</td><td>Started</td><td>Complete</td><td>Reviewed</td><td>Passed</td></tr>"

        for ci in bgc.statusHis:
            print "<tr>"
            print "<td>&nbsp;&nbsp;&nbsp;</td><td>{}</td>".format(ci)
            print status_to_row(bgc.statusHis[ci])
            print "</tr>"

        print "<tr><td colspan=2>To Volunteer:</td><td colspan=4>"
        pprint(bgc.items_needed(False))
        print "</td></tr>"
        print "<tr><td colspan=2>For Employment:</td><td colspan=4>"
        pprint(bgc.items_needed(True))
        print "</td></tr>"
    print "</table>"

elif model.HttpMethod == "get":
    bgc = BackgroundChecker()

    forEmployment = model.Data.emp != "" or (q.QueryCount('''
        (
            IsMemberOf( Org={0} ) = 1
            OR IsProspectOf( Org={0} ) = 1
        )
        AND PeopleId = {1}
        '''.format(employeeOrgId, str(bgc.person.PeopleId))) > 0)

    model.Header = "Background Check (Employee)" if forEmployment else "Background Check (Volunteer)"

    status = bgc.status_employ() if forEmployment else bgc.status_volunteer()

    print "<p>Thank you for serving at Tenth!  To protect our children, our other volunteers, and you, we require " \
          "background checks of all staff members and adult volunteers who work with children.</p> "

    if (status & 15) == 15:
        print "<p><b>You are currently cleared to serve as {}.</b></p>".format(
            "an employee" if forEmployment else "a volunteer")

    else:
        print "<p><b>You are NOT currently cleared to serve as {}.</b></p>".format(
            "an employee" if forEmployment else "a volunteer")

    to_do = bgc.items_needed(forEmployment)

    if len(to_do) == 0:
        print "<p>Your checks do not yet need renewal.  We will let you know when your action is required.</p>"
    else:
        print "<p>Your checks expire soon.  Please help us update them.</p>"

        # TODO remove items of review_*

        if 'Bio' in to_do:
            print "<div class=\"well\"><a href=\"/Person2/{}\">Click here to update your profile</a> to include your full name, gender, and " \
                  "date of birth.</div>".format(bgc.person.PeopleId)

        if 'Ssn' in to_do:
            print "<div class=\"well\">"
            print "<form method=\"POST\" action=\"/PyScriptForm/{}?set=ssn{}\">".format(model.ScriptName,
                                                                                        '&emp=1' if forEmployment else '')
            print "<table><tbody>"
            print "<tr><td style=\"width:200px;\">First Name</td><td><input type=\"text\" disabled=\"disabled\" " \
                  "value=\"{}\" /></td></tr>".format(bgc.person.FirstName)
            print "<tr><td>Middle Name or Initial</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" " \
                  "/></td></tr>".format(bgc.person.MiddleName)
            print "<tr><td>Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" /></td></tr>". \
                format(bgc.person.LastName)
            print "<tr><td>Maiden/Former Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"\" " \
                  "/></td></tr>".format(bgc.person.MaidenName or "")
            print "<tr><td>Gender</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" /></td></tr>".format(
                bgc.person.Gender.Description or "REQUIRED")

            print "<tr><td>Date of Birth</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}/{}/{}\" " \
                  "/></td></tr>".format(bgc.person.BirthMonth, bgc.person.BirthDay, bgc.person.BirthYear)

            print "<tr><td colspan=2>"
            print "<p>To correct any of the information above, <a href=\"/Person2/0#\">edit your profile</a>."
            print "<p>By submitting your Social Security Number below, you authorize Tenth to run a background check " \
                  "on you, and to continue to run background checks on you in the future in accordance with Tenth\'s " \
                  "Child Protection Policy, so long as you continue to work with Children in conjunction with the " \
                  "ministries of Tenth.</p> "
            print "<p>The results of the background check will be visible only to specific staff members.  In " \
                  "accordance with Pennsylvania law, they will not necessarily be available to you.  Your Social " \
                  "Security Number is not accessible by anyone.</p> "
            print "</td></tr>"
            print "<tr><td><label for=\"ssn\">SSN</label></td><td><input type=\"password\" id=\"ssn\" " \
                  "required=\"required\" name=\"ssn\" placeholder=\"000-00-0000\" maxlength=\"12\" pattern=\"[0-9]{" \
                  "3}-[0-9]{2}-[0-9]{4}\" /></td></tr> "
            print "<tr><td></td><td><input type=\"submit\" /></td></tr>"
            print "</tbody></table>"

            print "</form>"
            print "</div>"

        if 'receive_emp' in to_do or 'receive_vol' in to_do:
            print "<div class=\"well\">You should soon receive an email with instructions for how to complete the PA " \
                  "Child Abuse History Clearance.  That email includes a code which you should use in place of " \
                  "payment, and which ensures the clearance will come back to us. "
            print "<a href=\"mailto:clearances@tenth.org\">Let us know if you haven't received it within a few " \
                  "business days.</a>"  # TODO replace email with some kind of variable.
            print "</div>"

        if 'submit_fbi_aff' in to_do:
            print "<div class=\"well\">We need your FBI Fingerprinting clearance or an affidavit.  <br />"
            print "If you <b>have only lived in Pennsylvania within the last 10 years</b>, " \
                  "<a href=\"?view=affid\">please click here to sign an affidavit</a>.<br /> "
            print "If you <b>have lived outside Pennsylvania within the last 10 years</b>, we will need you to get an" \
                  " FBI fingerprint check.  Click here for full instructions.  Once you receive your " \
                  "certification in the mail, please scan it and upload it here. "
            print "</div>"

        if 'submit_fbi' in to_do:
            print "<div class=\"well\">We need your FBI Fingerprinting clearance.  Click here for full instructions. " \
                  "Once you receive your certification in the mail, please scan it and upload it here.</div>"


elif model.HttpMethod == "post":
    bgc = BackgroundChecker()

    forEmployment = model.Data.emp != "" or (q.QueryCount('''
        (
            IsMemberOf( Org={0} ) = 1
            OR IsProspectOf( Org={0} ) = 1
        )
        AND PeopleId = {1}
        '''.format(employeeOrgId, str(bgc.person.PeopleId))) > 0)

    to_do = bgc.items_needed(forEmployment)

    forEmployment = 1 if forEmployment else 0

    ssn = False
    submit = False
    if model.Data.set == "ssn" and model.Data.ssn != "":
        ssn = model.Data.ssn

    if 'submit_emp' in to_do:
        submit = 'ComboPS'  # TODO add employment distinguisher when it becomes available.
    elif 'submit_vol' in to_do:
        submit = 'ComboPS'
    elif 'submit_basic' in to_do:
        submit = 'Combo'

    if submit is not False and ssn is not False:
        model.AddBackgroundCheck(bgc.person.PeopleId, submit, 1, forEmployment, ssn, sPlusState=stateCode)

    elif submit is not False and ssn is False:
        model.AddBackgroundCheck(bgc.person.PeopleId, submit, 1, forEmployment, sPlusState=stateCode)

    print "REDIRECT={}/PyScript/{}".format(model.CmsHost, model.ScriptName)
