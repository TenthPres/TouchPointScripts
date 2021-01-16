import model
import q

import clr
from System import DateTime
from pprint import pprint

checkCode = "ComboPS"
employeeOrgId = 61


class BackgroundChecker:
    Statuses = {
        'NOT_RUN': 0,
        'CHECK_STARTED': 1,
        'CHECK_COMPLETE': 2,
        'REVIEW_COMPLETE': 4,
        'PASSED': 8,
        'CURRENT': 16,
        'NOT_EXPR_SOON': 32
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
        self.status_set = False
        self.status = {
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

        # get minors out of the way
        if not for_employment and (self.status['isMin'] & 32 == 32):
            return items  # if the subject is a minor not looking for employment, they need nothing.

        # Bio: Full Name, Email, etc.
        if ((for_employment and self.status['paEmp'] & 32 == 0) or
                self.status['paVol'] & 32 == 0 or
                self.status['basic'] & 32 == 0):
            items.append("Bio")

        # SSN
        if (self.person.SSN.IsNotNull() and (  # TODO check the logic here.
                for_employment and self.status['paEmp'] & 32 == 0) or
                self.status['paVol'] & 32 == 0 or
                self.status['basic'] & 32 == 0):
            items.append("SSN")

        # Submission  TODO this needs to be reworked because if an expiring cert is present, this won't work.
        if for_employment and self.status['paEmp'] & 1 == 0:
            items.append("submit_emp")
        elif self.status['paVol'] & 1 == 0:
            items.append("submit_vol")
        elif self.status['basic'] & 1 == 0:
            items.append("submit_basic")

        # Completion Actions  TODO this needs to be reworked because if an expiring cert is present, this won't work.
        if for_employment and self.status['paEmp'] & 1 == 1 and self.status['paEmp'] & 2 == 0:
            items.append("receive_emp")
        elif self.status['paVol'] & 1 == 1 and self.status['paVol'] & 2 == 0:
            items.append("receive_vol")
        elif self.status['basic'] & 1 == 1 and self.status['basic'] & 2 == 0:
            items.append("receive_basic")

        return items

    def can_employ(self):
        self.determine_status()
        return (self.status_employ() & 31) == 31

    def status_employ(self):
        self.determine_status()
        return self.status['basic'] & self.status['paEmp'] & self.status['fingr']

    def can_volunteer(self):
        self.determine_status()
        return (self.status_volunteer() & 31) == 31

    def status_volunteer(self):
        return (self.status['basic'] & self.status['paVol'] & (self.status['affid'] | self.status['fingr'])) | \
               self.status['isMin']

    def determine_status(self):
        if self.status_set:
            return

        checks_sql = "SELECT TOP 20 * FROM [BackgroundChecks] WHERE [PeopleId] = @p1 AND DATEDIFF(DAY, DATEADD(YEAR, -10, GETDATE()), [Updated]) > 0 ORDER BY [Updated] DESC".format(
            self.person.PeopleId)
        for check in q.QuerySql(checks_sql, self.person.PeopleId):
            if check.ServiceCode == "ComboPS":
                # Basic + PA Volunteer + (maybe) PA Employee (PA Employee fulfills PA Volunteer)

                validForEmp = DateTime.Compare(check.Updated, self.Expirations['paVol']) > 0 and (
                        check.ReportLabelID == 1)
                validForVol = DateTime.Compare(check.Updated, self.Expirations['paEmp']) > 0

                if check.StatusID >= 2:  # Check has been triggered.
                    if validForVol:
                        self.status['paVol'] = self.status['paVol'] | self.Statuses['CHECK_STARTED']
                    if validForEmp:
                        self.status['paEmp'] = self.status['paEmp'] | self.Statuses['CHECK_STARTED']

                    # Check if expiring soon
                    if DateTime.Compare(check.Updated, self.Renewals['paVol']) > 0 and validForVol:
                        self.status['paVol'] = self.status['paVol'] | self.Statuses['NOT_EXPR_SOON']
                    if DateTime.Compare(check.Updated, self.Renewals['paEmp']) > 0 and validForEmp:
                        self.status['paEmp'] = self.status['paEmp'] | self.Statuses['NOT_EXPR_SOON']

                if check.StatusID == 3:
                    if validForVol:
                        self.status['paVol'] = self.status['paVol'] | self.Statuses['CHECK_COMPLETE'] | self.Statuses[
                            'CURRENT']
                    if validForEmp:
                        self.status['paEmp'] = self.status['paEmp'] | self.Statuses['CHECK_COMPLETE'] | self.Statuses[
                            'CURRENT']

                    if check.IssueCount == 0:
                        if validForVol:
                            self.status['paVol'] = self.status['paVol'] | self.Statuses['REVIEW_COMPLETE'] | \
                                                   self.Statuses['PASSED']
                        if validForEmp:
                            self.status['paEmp'] = self.status['paEmp'] | self.Statuses['REVIEW_COMPLETE'] | \
                                                   self.Statuses['PASSED']

                    else:
                        print "This program does not yet handle checks with issues."  # TODO

            if check.ServiceCode == "Combo" or check.ServiceCode == "ComboPS":

                # Check if expired
                if DateTime.Compare(check.Updated, self.Expirations['basic']) > 0:

                    if check.StatusID >= 2:  # Check has been triggered.
                        self.status['basic'] = self.status['basic'] | self.Statuses['CHECK_STARTED']

                        # Check if expiring soon
                        if DateTime.Compare(check.Updated, self.Renewals['basic']) > 0:
                            self.status['basic'] = self.status['basic'] | self.Statuses['NOT_EXPR_SOON']

                    if check.StatusID == 3:
                        self.status['basic'] = self.status['basic'] | self.Statuses['CHECK_COMPLETE'] | self.Statuses[
                            'CURRENT']

                        if check.IssueCount == 0:
                            self.status['basic'] = self.status['basic'] | self.Statuses['REVIEW_COMPLETE']
                            self.status['basic'] = self.status['basic'] | self.Statuses['PASSED']

                        else:
                            print "This program does not yet handle checks with issues."

        if self.person.BirthDate > self.Expirations['isMin']:
            self.status['isMin'] = self.Statuses['CHECK_STARTED'] | self.Statuses['CHECK_COMPLETE'] | self.Statuses[
                'REVIEW_COMPLETE'] | self.Statuses['PASSED'] | self.Statuses['CURRENT']
            if self.person.BirthDate > self.Renewals['isMin']:
                self.status['isMin'] = self.status['isMin'] | self.Statuses['NOT_EXR_SOON']

        self.status_set = True


# DETERMINE WHAT TO SHOW

userPerson = model.GetPerson(model.UserPeopleId)

if model.Data.view == "list" and userPerson.Users[0].InRole('Admin'):

    model.Styles = "<style>.y { background: #dfd;} .n { background: #fdd; }</style>"


    def statusToCell(status, mask):
        return "<td class=\"{}\">{}</td>".format(("y" if status & mask == mask else "n"),
                                                 ("Yes" if status & mask == mask else "No"))


    def statusToRow(status):
        r = ""
        r += statusToCell(status, 1)
        r += statusToCell(status, 2)
        r += statusToCell(status, 4)
        r += statusToCell(status, 8)
        r += statusToCell(status, 16)
        r += statusToCell(status, 32)
        return r


    print "<table style=\"width:100%;\">"

    for p in q.QuerySql("SELECT [PeopleId] FROM [BackgroundChecks] GROUP BY [PeopleId]"):
        bgc = BackgroundChecker(p.PeopleId)
        print "<tr>"
        print "<th colspan=4>{} {}</th>".format(bgc.person.PreferredName, bgc.person.LastName)
        print "<td colspan=2>{}</td>".format("Employable" if bgc.can_employ() else "Not Employable")
        print "<td colspan=2>{}</td>".format("Volunteer" if bgc.can_volunteer() else "No Volunteering")
        print "</tr>"

        print "<tr><td>&nbsp;&nbsp;&nbsp;</td><td>Check</td><td>Started</td><td>Complete</td><td>Reviewed</td><td>Passed</td><td>Not Expired</td><td>Not Expiring</td></tr>"

        for ci in bgc.status:
            print "<tr>"
            print "<td></td><td>{}</td>".format(ci)
            print statusToRow(bgc.status[ci])
            print "</tr>"

    print "</table>"

elif model.HttpMethod == "get":
    bgc = BackgroundChecker()

    forEmployment = model.Data.emp != "" or model.InOrg(bgc.person.PeopleId, employeeOrgId)

    model.Header = "Background Check (Employee)" if forEmployment else "Background Check (Volunteer)"

    status = bgc.status_employ() if forEmployment else bgc.status_volunteer()

    form = ""

    if (status & 32) == 32:
        form += "<p>No Updates are required.</p>"

    else:
        form += "<p>We need to run an update.</p>"

    model.Form = form

# if (model.HttpMethod == "get"):
#
#     formSql = "SELECT p.FirstName, p.LastName, p.MiddleName, p.MaidenName, gender.Code as sex, p.BirthMonth, p.BirthDay, p.BirthYear FROM People as p LEFT JOIN lookup.Gender as gender ON p.GenderId = gender.Id WHERE p.PeopleId = @p1"
#     pInfo = q.QuerySqlTop1(formSql, pid)
#
#     form = "<form method=\"POST\">"
#
#     form += "<p>Thank you for serving at Tenth!  To protect our children, our other volunteers, and you, we require background checks of all staff members and adult volunteers who work with children.</p>"
#
#     form += "<table><tbody>"
#
#     form += "<tr><td>First Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + pInfo.FirstName + "\" /></td></tr>"
#
#     form += "<tr><td>Middle Name or Initial</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + (
#                 pInfo.MiddleName or "") + "\" /></td></tr>"
#
#     form += "<tr><td>Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + pInfo.LastName + "\" /></td></tr>"
#
#     form += "<tr><td>Maiden/Former Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + (
#                 pInfo.MaidenName or "") + "\" /></td></tr>"
#
#     form += "<tr><td>Gender</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + (
#                 pInfo.sex or "REQUIRED") + "\" /></td></tr>"
#
#     form += "<tr><td>Date of Birth</td><td><input type=\"text\" disabled=\"disabled\" value=\"" + str(
#         pInfo.BirthMonth) + "/" + str(pInfo.BirthDay) + "/" + (str(pInfo.BirthYear) or "REQUIRED") + "\" /></td></tr>"
#
#     form += "<tr><td></td><td>To correct any of the information above, <a href=\"/Person2/0#\">edit your profile</a>.</td></tr>"
#
#     form += "<tr><td><label for=\"ssn\">SSN</label></td><td><input type=\"password\" id=\"ssn\" required=\"required\" name=\"ssn\" placeholder=\"###-##-####\" maxlength=\"12\" pattern=\"[0-9]{3}-[0-9]{2}-[0-9]{4}\" /></td></tr>"
#
#     form += "</tbody></table>"
#
#     form += "<p>By submitting this form, you authorize Tenth to run a background check on you, and to continue to run background checks on you in the future in accordance with Tenth's Child Protection Policy, so long as you continue to work with Children in conjunction with the ministries of Tenth.</p>"
#
#     form += "<p>The results of the background check will be visible only to specific staff members.  In accordance with Pennsylvania law, they will not necessarily be available to you.  Your Social Security Number is not accessible by anyone.</p>"
#
#     form += "<input type=\"submit\" />"
#
#     model.Form = form + "</form>"
#     model.Header = "New Background Check"
#
# else:
#
#     model.AddBackgroundCheck(pid, checkCode, 1, 0, model.Data.ssn)
#
#     print("<p>Thank you.  Your background check will be processed shortly.</p>")
#
#     # model.Form = model.JsonSerialize([])
#
#     # print(model.JsonSerialize(model))
#
#     # print(pid)
