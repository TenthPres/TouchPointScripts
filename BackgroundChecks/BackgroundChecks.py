# noinspection PyUnresolvedReferences

# Pckgd
# Title: PA Background Checks
# Description: Make Pennsylvania background checks just a little better.
# Updates from: GitHub/TenthPres/TouchPointScripts/BackgroundChecks/BackgroundChecks.py
# Author: James at Tenth
# Requires: BackgroundChecks-Status.sql

from System import DateTime, String, Convert

global model, Data

mainQuery = model.SqlContent('BackgroundChecks-Status')



userPerson = model.GetPerson(model.UserPeopleId)
subjectPid = userPerson.PeopleId
model.Header = "Background Checks"
impersonated = False

# handle viewas impersonation
if (Data.viewas != '' and userPerson.Users[0].InRole('BackgroundCheck')):
    subjectPid = Data.viewas
    impersonated = True


def actionForDate(d):
    if d is None:
        return "None"
    if DateTime.Compare(d, DateTime.Now) < 0:
        return "Expired"
    if DateTime.Compare(d, DateTime.Now.AddMonths(3)) < 0:
        return "Expires Soon"
    return "Valid"


def formatDate(d, color=True):
    if color:
        a = actionForDate(d)
    else:
        a = "unformatted"

    s = d.ToString("MMMM d, yyyy")
    if a == "Expired":
        return "<span style=\"background-color:red;\">{} on {}</span>".format(a, s)

    if a == "Expires Soon":
        return "<span style=\"background-color:yellow;\">{}: {}</span>".format(a, s)

    if a == "unformatted":
        return "{}".format(s)

    return "<span>{} until {}</span>".format(a, s)

def needs(r, p):  # row, person
    n = []
    forEmp = r.Employee == "Employee"

    if p.MemberStatusId == 50:
        n.append('JuAdd')

    # Get minors out of the way
    if actionForDate(r.Minor) == "Valid":
        return n

    # Bio: Full Name, Email, etc.
    if (
            String.IsNullOrEmpty(p.FirstName) or
            String.IsNullOrEmpty(p.LastName) or
            (p.GenderId != 1 and p.GenderId != 2) or
            p.BirthYear < 1930  # meant to detect if null
    ):
        n.append('Bio')
        n.append('Invalid')

    if len(n) > 0:
        return n

    needSsn = False

    if forEmp:
        if actionForDate(r.CAHC) != "Valid" or actionForDate(r.PATCH) != "Valid":
            if r.InProgressLastUpdate is None:
                n.append("PMM Emp")
                needSsn = True
            else:
                n.append("PMM Completion")

        if actionForDate(r.FBI) != "Valid":
            n.append("FBI Emp")

    else:
        if actionForDate(r.CAHC) != "Valid" or actionForDate(r.PATCH) != "Valid":
            if r.InProgressLastUpdate is None:
                n.append("PMM Vol")
                needSsn = True
            else:
                n.append("PMM Completion")

        if actionForDate(r.FBI) != "Valid" and actionForDate(r.Aff) != "Valid":
            n.append("FBI Vol")

    # SSN
    if String.IsNullOrEmpty(p.Ssn) and needSsn:
        n.append('Ssn')

    if actionForDate(r.Training) != "Valid":
        if r.TrainAssign is None or r.Training > r.TrainAssign:
            n.append("Train Assign")
        else:
            n.append("Train Completion")

    return n


# List mode
if (model.Data.view == "list" and (userPerson.Users[0].InRole('BackgroundCheck') or userPerson.Users[0].InRole('BackgroundCheckLight'))) or (model.Data.view == "admin" and userPerson.Users[0].InRole('Admin')):
    model.Styles = "<style>.y { background: #dfd;} .n { background: #fdd; } .box-content a:not(.btn) {text-decoration: underline;}</style>"

    adminMode = (model.Data.view == "admin" and userPerson.Users[0].InRole('Admin'))

    for r in q.QuerySql(mainQuery):

        cls = 'y' if not r.Status == "Invalid" else 'n'

        print "<div class=\"well {}\">".format(cls)
        print "<h2>{} {}</h2>".format(r.GoesBy, r.LastName)
        print "<p><b>"
        if r.Employee == "Employee":
            print "  {}  ".format("Employable with Children" if not r.Status == "Invalid" else "Not Employable with Children")
        else:
            print "  {}  ".format("Volunteer with Children" if not r.Status == "Invalid" else "No Volunteering with Children")
        print "</b>"
        if userPerson.Users[0].InRole('BackgroundCheck'):
            print "<a href=\"https://my.tenth.org/Person2/{}#tab-volunteer\">Documents</a> ".format(r.PeopleId)
            print "<a href=\"?viewas={}\">Impersonate</a>".format(r.PeopleId)
        print "</p>"

        print "<h3>Documents On-Hand</h3>"
        print "<ul>"
        hasDocs = False
        if r.Minor is not None:
            print "<li>Minor: {}</li>".format(formatDate(r.Minor))
            hasDocs = True

        if r.CAHC is not None:
            print "<li>CAHC: {}</li>".format(formatDate(r.CAHC))
            hasDocs = True

        if r.PATCH is not None:
            print "<li>PATCH: {}</li>".format(formatDate(r.PATCH))
            hasDocs = True

        if r.FBI is not None:
            print "<li>FBI: {}</li>".format(formatDate(r.FBI))
            hasDocs = True

        if r.Aff is not None:
            print "<li>Affidavit: {}</li>".format(formatDate(r.Aff))
            hasDocs = True

        if r.Training is not None:
            print "<li>Training: {}</li>".format(formatDate(r.Training))
            if r.TrainAssign is not None and r.TrainAssign > r.Training:
                print "  Assigned {}".format(formatDate(r.TrainAssign, False))
            print "</li>"

        print "</ul>"

        if not hasDocs:
            print "<p><i>No Documents</i></p>"

        n = needs(r, model.GetPerson(r.PeopleId))
        if len(n) > 0 or r.InProgressLastUpdate is not None:
            print "<h3>Action Required</h3>"
            print "<ul>"

            if 'JuAdd' in n:
                print "<li>Admin staff must reconcile this person's \"Just Added\" status.</li>"

            if 'Bio' in n:
                print "<li>Subject must update their profile to include full name, gender, and date of birth.</li>"

            if 'Ssn' in n:
                print "<li>Subject must submit for a background check, including providing their SSN.</li>"

            elif 'PMM Emp' in n or 'PMM Vol' in n:
                print "<li>Subject must submit for a background check renewal.</li>"

            if 'PMM Completion' in n or r.InProgressLastUpdate is not None:
                if r.Status == "Invalid":
                    print "<li>Subject must complete the PMM process to get their CAHC results.</li>"
                else:
                    print "<li>Admin staff should check that their background check is appropriately marked as approved.</li>"

            if 'FBI Vol' in n:
                print "<li>Subject must complete FBI fingerprinting or an affidavit.</li>"

            if 'FBI Emp' in n:
                print "<li>Subject must complete FBI fingerprinting.</li>"

            if 'Train Assign' in n:
                print "<li>Subject needs to have training assigned to them.</li>"

            if 'Train Completion' in n:
                print "<li>Subject needs to complete training which was assigned on {}.</li>".format(formatDate(r.TrainAssign, False))

            print "</ul>"


        if adminMode:
            p = model.GetPerson(r.PeopleId)
            print "<p><b>Needed:</b> {}</p>".format(n)

        print "</div>"

# Tagging mode
elif model.Data.view == "tag" and userPerson.Users[0].InRole('BackgroundCheck'):

    tagOwner = userPerson.PeopleId
    prefix = "Background Check: "

    tagsToIgnore = ['Ssn', 'Bio', 'Invalid']
    tags = ['FBI Emp', 'FBI Vol', 'Train Completion', 'Train Assign', 'PMM Completion', 'PMM Vol', 'PMM Emp']

    for t in tags:
        model.ClearTag(prefix + t, tagOwner)


    for r in q.QuerySql(mainQuery):
        nl = needs(r, model.GetPerson(r.PeopleId))

        for n in nl:
            if n in tagsToIgnore:
                continue
            if n not in tags:
                print "<p>Error: could not find the tag '{}' in the standard.</p>".format(n)
            else:
                model.AddTag(r.PeopleId, "Background Check: " + n, tagOwner, False)

    print "<p>Done!</p>"



# Affidavit creation mode
elif model.Data.view == "affid":
    sql = "{0} WHERE PeopleId = {1}".format(mainQuery, subjectPid)

    hasResult = False
    for r in q.QuerySql(sql):
        model.Header = "PA Resident Affidavit"

        if r.Employee == "Employee":
            print "<p>As you are an employee, you are not eligible for the affidavit.  Please go back to complete the process.</p>"

        elif actionForDate(r.Affid) != "Valid":

            print "<p>Please complete and sign the form below.  Once you do, you'll need to confirm your email.  Then, it may take a few minutes for the change to be reflected in your profile. <b>Do NOT submit this form multiple times.</b></p>"

            print '''<iframe src="https://na2.documents.adobe.com/public/esignWidget?wid=CBFCIBAA3AAABLblqZhAbxJ_V6VBKJe1Yp-Ea5w47T43MbHLt4KcNzv1Rz1HQ6nAg2B7qbaFhIVaP2niSMbA*&hosted=false#PersonId={}" width="100%" height="100%" frameborder="0" style="border: 0; height: 80vh; overflow: hidden; min-height: 500px;"></iframe>'''.format(r.PeopleId)

        else:
            print "<p>It appears that you already have an affidavit in progress or on file.</p>"

# Submission
elif model.HttpMethod == "post":
    sql = "{0} WHERE PeopleId = {1}".format(mainQuery, subjectPid)

    hasResult = False
    for r in q.QuerySql(sql):
        forEmployment = (r.Employee == "Employee")
        ssn = False
        if model.Data.set == "ssn" and model.Data.ssn != "":
            ssn = model.Data.ssn

        p = model.GetPerson(r.PeopleId)
        n = needs(r, p)

        package = False
        submit = False

        if 'PMM Emp' in n or 'PMM Vol' in n:
            if forEmployment:
                package = "PA Employee"
            else:
                if p.PrimaryState == 'PA':
                    package = "PA Package"
                else:
                    package = "PA Volunteer"

            if package is not False and ssn is not False:
                submit = model.AddBackgroundCheck(r.PeopleId, package, sSSN=ssn)

            elif package is not False and ssn is False:
                submit = model.AddBackgroundCheck(r.PeopleId, package)

            if submit != False:
                print "REDIRECT={}/PyScript/{}".format(model.CmsHost, model.ScriptName)
            else:
                print submit
                print "<p>Something weird happened.  Please contact the church office, and give them this exact message.</p>"

        elif 'PMM Completion' in n:
            # We can't actually do anything with this, so go back to the other view and hope it's not a circle.
            print "REDIRECT={}/PyScript/{}".format(model.CmsHost, model.ScriptName)

        else:
            print "<p>Something strange happened.  Please contact the church office, and give them this exact message.</p>"


# Default user view
else:
    model.Styles = "<style>.y { background: #dfd;} .n { background: #fdd; } .box-content a:not(.btn) {text-decoration: underline;}</style>"

    print "<p>"
    if userPerson.Users[0].InRole('BackgroundCheck') or userPerson.Users[0].InRole('BackgroundCheckLight'):
        print "<a href=\"?view=list\" class=\"btn btn-default\">List View</a>  "
        print "<a href=\"/RunScript/BackgroundChecks-Status\" class=\"btn btn-default\">Grid View</a>  "
        print "<a href=\"/PyScript/BackgroundCheckStats\" class=\"btn btn-default\">Stats</a>  "

    if userPerson.Users[0].InRole('BackgroundCheck'):
        print "<a href=\"?view=tag\" class=\"btn btn-default\">Update Tags</a>  "

    if userPerson.Users[0].InRole('Admin'):
        print "<a href=\"?view=admin\" class=\"btn btn-default\">Technical Admin View</a>  "
    print "</p>"

    sql = "{0} WHERE PeopleId = {1}".format(mainQuery, subjectPid)

    hasResult = False
    for r in q.QuerySql(sql):
        hasResult = True
        p = model.GetPerson(r.PeopleId)
        n = needs(r, p)
        forEmployment = (r.Employee == "Employee")

        model.Header = "Background Check (Employee)" if forEmployment else "Background Check (Volunteer)"

        if impersonated:
            model.Header = model.Header + " [{} {}]".format(r.GoesBy, r.LastName)

        print "<p>Thank you for serving at Tenth!  To protect our children, our other volunteers, and you, we require " \
              "background checks of all staff members and adult volunteers who work with children.</p> "

        if r.Status != "Invalid":
            print "<p><b>You are currently cleared to serve as {}.</b></p>".format(
                "an employee" if forEmployment else "a volunteer")

        else:
            print "<p><b>You are NOT currently cleared to serve as {}.</b></p>".format(
                "an employee" if forEmployment else "a volunteer")

        if len(n) == 0:
            print "<p>Your checks do not yet need renewal.  We will let you know when your action is required.</p>"
        else:
            print "<p>Your checks expire soon.  Please help us update them, following each of the steps below.</p>"
            print '<!-- Item codes: {} -->'.format(n)

        if 'JuAdd' in n:
            print "<div class=\"well\">Your profile needs to be established by a staff member before we can continue " \
                  "through this process.  <a href=\"mailto:dbhelp@tenth.org?subject=Please+convert+my+profile+to+not" \
                  "+Just+Added\">Email us (email is pre-written for you) to let us know we need to do " \
                  "this.</a></div>".format(p.PeopleId)

        if 'Bio' in n:
            print "<div class=\"well\"><p>Please update your profile to include your " \
                  "full name, gender, and date of birth.</p><p><a href=\"/Person2/{}\" " \
                  "class=\"btn btn-primary\">Update Your Profile</a></p></div>".format(subjectPid)

        elif 'Ssn' in n:
            print "<div class=\"well\">"
            print "<form method=\"POST\" action=\"/PyScriptForm/{}?set=ssn{}\">". \
                format(model.ScriptName, '&emp=1' if forEmployment else '')
            print "<table><tbody>"
            print "<tr><td style=\"width:200px;\">First Name</td><td><input type=\"text\" disabled=\"disabled\" " \
                  "value=\"{}\" /></td></tr>".format(p.FirstName)
            print "<tr><td>Middle Name or Initial</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" " \
                  "/></td></tr>".format(p.MiddleName)
            print "<tr><td>Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" /></td></tr>". \
                format(p.LastName)
            print "<tr><td>Maiden/Former Last Name</td><td><input type=\"text\" disabled=\"disabled\" value=\"\" " \
                  "/></td></tr>".format(p.MaidenName or "")
            print "<tr><td>Gender</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}\" /></td></tr>".format(
                p.Gender.Description or "REQUIRED")

            print "<tr><td>Date of Birth</td><td><input type=\"text\" disabled=\"disabled\" value=\"{}/{}/{}\" " \
                  "/></td></tr>".format(p.BirthMonth, p.BirthDay, p.BirthYear)

            print "<tr><td colspan=2>"
            print "<p>To correct any of the information above, <a href=\"/Person2/0#\">edit your profile</a>."
            print "<p>By submitting your Social Security Number below, you authorize Tenth to run a background " \
                  "check on you and to renew background checks as required by Pennsylvania law and/or Tenth's " \
                  "Child Protection Policy</p> "
            print "<p>The results of the background check will be held in confidence. Your Social " \
                  "Security Number is encrypted, and not accessible by anyone.</p>"
            print "</td></tr>"
            print "<tr><td><label for=\"ssn\">SSN</label></td><td><input type=\"password\" id=\"ssn\" " \
                  "required=\"required\" name=\"ssn\" placeholder=\"000-00-0000\" maxlength=\"12\" pattern=\"[0-9]{" \
                  "3}[-]?[0-9]{2}[-]?[0-9]{4}\" /></td></tr> "
            print "<tr><td></td><td><input type=\"submit\" class=\"btn btn-primary\" /></td></tr>"
            print "</tbody></table>"

            print "</form>"
            print "</div>"

        elif 'PMM Emp' in n or 'PMM Vol' in n:
            print "<div class=\"well\">"

            print "<form method=\"POST\" action=\"/PyScriptForm/{}\">".format(model.ScriptName)
            print "<table><tbody>"
            print "<tr><td><p>You're all set for a mostly-automated renewal.  Click to continue.</p></td></tr>"
            print "<tr><td><input class=\"btn btn-primary\" type=\"submit\" /></td></tr>"
            print "</tbody></table>"

            print "</form>"
            print "</div>"

        if 'PMM Completion' in n:
            print "<div class=\"well\">Within one or two business days, you should receive an email with instructions " \
                  "for how to complete the PA Child Abuse History Clearance.  The subject line will probably be \"PA Child " \
                  "Abuse Registry Check - Tenth Presbyterian Church\".  " \
                  "That email includes a code which you should use in place of " \
                  "payment, and which ensures the clearance will come back to us. "
            print "<a href=\"mailto:clearances@tenth.org\">Let us know if you haven't received it within a few " \
                  "business days.</a>"
            print "</div>"

        if 'FBI Vol' in n:
            print "<div class=\"well\">We need your FBI Fingerprinting clearance or an affidavit.  <ul>"
            print "<li>If you <b>have only lived in Pennsylvania within the last 10 years</b>, " \
                  "<a href=\"?view=affid\">please click here to sign an affidavit</a>.</li>"
            print "<li>If you <b>have lived outside Pennsylvania within the last 10 years</b>, we will need you to get an" \
                  " FBI fingerprint check.  Pennsylvania uses IdentoGo as a provider for this service.  Either make your " \
                  "appointment at a location in PA (STRONGLY suggested), or use the \"Card Submission By Mail\" option, " \
                  "which will provide instructions for completing a fingerprint card and submitting it back to " \
                  "IdentoGo. (This is much LESS convenient than it sounds, and also more expensive.)  " \
                  "<a href=\"https://uenroll.identogo.com/workflows/1KG6ZJ/appointment/bio\"" \
                  " target=\"_blank\">Click here to enter your information and arrange a fingerprinting " \
                  "appointment.</a>  " \
                  "Once you receive your certification in the mail, please scan it and " \
                  "<a href=\"/OnlineReg/96\" >upload it here</a>.</li>"
            print "<li>If you <b>already have the fingerprinting credential</b> because of your work or volunteering elsewhere, you can " \
                  "<a href=\"/OnlineReg/96\" >upload it here</a>.  The body of the document should begin with " \
                  "\"Your fingerprint based record check\"...</li>"
            print "</ul></div>"

        if 'FBI Emp' in n:
            print "<div class=\"well\">We need your FBI Fingerprinting clearance. Please make an appointment for fingerprinting. " \
                  "Pennsylvania uses IdentoGo as a provider for this service, and you will be " \
                  "required to make an appointment at a location in PA.  A few weeks after your appointment, " \
                  " your certification will be mailed to you.  Please scan it and upload it here."
            print "<br /><a href=\"https://uenroll.identogo.com/workflows/1KG756/appointment/bio\" class=\"btn btn-primary\">Make Appointment</a>&nbsp;<a href=\"/OnlineReg/96\" class=\"btn btn-primary\">Submit Document</a>"
            print "</div>"

        if 'Train Assign' in n:
            print "<div class=\"well\">We need you to complete training on preventing sexual abuse of children.  We will be in touch with instructions."
            print "</div>"

        if 'Train Completion' in n:
            print "<div class=\"well\">We need you to complete training on preventing sexual abuse of children.  You should have received an email about this from MinistrySafe (our training partner) on or around {}.".format(formatDate(r.TrainAssign, False))
            print "</div>"

    if not hasResult:
        print "<p>We are under the impression that you do not serve in an area that requires a background check.  If this is not correct, please contact the church office."
        print "</p>"

    print "<p>If you have questions or need help, please email <a href=\"mailto:clearances@tenth.org\">clearances@tenth.org</a> or <a href=\"https://outlook.office365.com/owa/calendar/TenthPresbyterianChurch@tenth.org/bookings/s/2llJyCFr80Scs1p6QV919w2\">make an appointment here</a>.</p>"