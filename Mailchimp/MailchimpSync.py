# Roles=Admin
# MailchimpSync

import json
from datetime import datetime, date, timedelta
from pprint import pprint

# The accounts list should be a list of the MailChimp accounts you wish to import.
# The mcUser is the username (or email) you use to sign in to Mailchimp.
# The mcApiKey is the API Key from the Mailchimp UI (See Touchpoint's instructions for how to get that).  The -usX suffix must be
#               included on the end, as that indicates which server should be used for the API.
# The orgId is one of the following:
#   - a number - The org Id number of the org you want current subscribers to be imported into. If you only have one list in the
#               Mailchimp account, this will be fine.
#   - None -    This creates a new org for the purpose.  It will give the org an extra value that links it to the MailChimp list,
#               so that if you run the import again, it won't create a new list again.
#
#               If you have multiple lists in a single account, set orgId as None to have all new orgs created, or add the extra
#               value "MailChimpListId" as the 10-digit hex ID Mailchimp uses as a list ID.

accounts = [
    #    {
    #        "mcUser": "xxxxxxxxxxxx",
    #        "mcApiKey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-usX",
    #        "orgId": None
    #    }
]

# Give an OrgId to use as a template for new Involvements that may be created with the import.
orgToCopy = 78

# To import and link new list data (i.e. create new Orgs from existing lists) every time the script runs, set this to
# True.  To not import and link new lists at all, set this to False.  To only import new lists when the script is run
# manually (not as part of the Morning Batch), set this to None.  This does not impact the syncing of already-linked
# lists/orgs.  Setting this false saves computation time, which is useful if new lists aren't created very often.
importLists = None

# Mailchimp Interest Categories and Interests will be imported into TouchPoint as Sub-Groups and kept synchronized.  By
# default, the subgroups will be named in the format "Category Title :: Interest Name".  Change this setting to change
# the separator.  The separator needs to be distinct.  That is, it needs to be a pattern that you probably don't have in
# subgroups otherwise. To prevent Categories and Interests from being synchronized, set this to None.
categoryInterestSeparator = " :: "

# The TouchPoint PeopleId will be saved into a Merge field in TouchPoint.  This allows future syncs to run more
# efficiently. If you would like to change the name of the merge field, do so here.  You probably do not need to change
# this.  Must be all-caps. 
peopleIdMergeName = "TP_PID"

# Great job. That's all the setup you need to do.

########################################################################################################################


headers = {'content-type': 'application/json'}
model.Title = "Mailchimp Sync"


def DateTimeFromIso(dtStr):  # Replace with native if TouchPoint upgrades Python to 3.2+  Or, use a C# method.
    # parse the date/time
    return datetime.strptime(dtStr, '%Y-%m-%dT%H:%M:%S')  # Assumes UTC!


def RestGet(url, account):
    if 'mcLoginId' in account:
        returnValue = model.RestGet(url, headers, account['mcLoginId'], account['mcApiKey'])
    else:
        returnValue = model.RestGet(url, headers, account['mcUser'], account['mcApiKey'])
    return json.loads(returnValue)


def RestPost(url, account, data):
    loginUser = account['mcLoginId'] or account['mcUser']
    pprint({"user": loginUser, "pass": account['mcApiKey']})
    returnValue = model.RestPostJson(url, headers, data, loginUser, account['mcApiKey'])
    return json.loads(returnValue)


def GetEndpoint(l):
    return "https://{0}.api.mailchimp.com/3.0/".format(l['mcApiKey'].split('-')[1])


def GetSubgroups(l):
    if categoryInterestSeparator is None:
        return {}

    interestCategoriesEndpoint = GetEndpoint(
        l) + "lists/{0}/interest-categories?fields=categories.id,categories.title".format(l['mcListId'])
    interestCategories = RestGet(interestCategoriesEndpoint, l)['categories']

    subgroups = {}

    for ic in interestCategories:
        interestsEndpoint = GetEndpoint(
            l) + "lists/{0}/interest-categories/{1}/interests?fields=interests.id,interests.name".format(l['mcListId'],
                                                                                                         ic['id'])
        interests = RestGet(interestsEndpoint, l)['interests']

        for i in interests:
            subgroups[i['id']] = "{0}{1}{2}".format(ic['title'], categoryInterestSeparator, i['name'])

    return subgroups


# Transfers the status of Mailchimp to TouchPoint
def SyncPersonMailchimpToTouchPoint(m, l, peopleId):
    if m['status'] == 'subscribed':
        # Add, if not already.
        if not model.InOrg(peopleId, l['orgId']):
            try:
                model.AddMemberToOrg(peopleId, l['orgId'])
                print " - add</p>"
            except SystemError as e:
                print " - Error</p>"
                return

        # Update subgroups
        if 'interests' in m and categoryInterestSeparator is not None:
            for sgid in m['interests']:
                sgn = l['subgroups'][sgid]
                pprint(sgn)
                # if m['interests'][sgid] is False and model.InSubGroup(peopleId, l['orgId'], sgn):
                #     model.RemoveSubGroup(peopleId, l['orgId'], sgn)
                # elif m['interests'][sgid] is True and not model.InSubGroup(peopleId, l['orgId'], sgn):
                #     model.AddSubGroup(peopleId, l['orgId'], sgn)

    elif m['status'] == 'unsubscribed' or m['status'] == 'archived':
        # Drop, if not already.
        if model.InOrg(peopleId, l['orgId']):
            print " - dropped</p>"
            model.DropOrgMember(peopleId, l['orgId'])

    elif m['status'] == 'cleaned':
        # Drop, if not already.
        if model.InOrg(peopleId, l['orgId']):
            print " - cleaned</p>"
            model.DropOrgMember(peopleId, l['orgId'])

        # Potentially, cleaned addresses should be removed from TouchPoint records.  This is where to do that.

    # Note: Contacts with Mailchimp status 'pending' are imported as People records, but are not added to the Org

    if peopleIdMergeName not in m['merge_fields']:
        return {
            'merge_fields': {
                peopleIdMergeName: peopleId
            },
            'email_address': m['email_address'],
            'status': m['status']
        }
    return None


def SyncPersonTouchPointToMailchimp(emailAddress, l, p, transaction=None):
    ret = {
        'merge_fields': {
            peopleIdMergeName: p.PeopleId,
            'FNAME': p.PreferredName,
            'LNAME': p.LastName
        },
        'email_address': emailAddress,
        'status': None
    }
    
    # Skip cases where the person has probably already been synced. 
    if transaction is not None:
        if l['mcLastUpdated'] >= transaction.TransactionDate:
            return None

    # Subscribed - Either current, non-pending member, or
    if transaction is None \
            or (transaction.TransactionTypeId == 1 and transaction.Pending is False) \
            or transaction.TransactionTypeId == 3:  # TransactionTypeId == 1 => "Join" , 3 => "Change", else => "Drop",
        ret['status'] = 'subscribed'

        # Update Subgroups/Interests
        if categoryInterestSeparator is not None and len(l['subgroups']) > 0:
            # noinspection SqlResolve
            interestSql = """
            SELECT mt.Name FROM OrgMemMemTags ommt 
            LEFT JOIN MemberTags mt ON ommt.MemberTagId = mt.Id 
            WHERE ommt.OrgId=@orgId AND ommt.PeopleId=@peopleId AND mt.Name LIKE '%@separator%'
            """
            interestSql = interestSql.replace('@peopleId', str(p.PeopleId)).replace('@orgId', str(l['orgId'])).replace(
                '@separator', categoryInterestSeparator)
            ret['interests'] = l['subgroups']
            for intSql in q.QuerySql(interestSql):
                for k, intName in ret['interests'].items():
                    if str(intSql.Name) == str(intName):
                        ret['interests'][k] = True
            for k, v in ret['interests'].items():
                if v is not True:
                    ret['interests'][k] = False

    else:
        ret['status'] = 'unsubscribed'

    return ret


def SyncMailchimpMember(m, l):
    # Find or Create Mailchimp Member in TouchPoint
    peopleId = None
    if peopleIdMergeName in m['merge_fields'] and m['merge_fields'][peopleIdMergeName] is not '':
        peopleId = m['merge_fields'][peopleIdMergeName]

        # Make sure PeopleID is actually valid
        # noinspection SqlResolve
        peopleId = q.QuerySqlTop1("SELECT PeopleId from People WHERE PeopleId = {}".format(peopleId))

        if peopleId is not None:
            peopleId = peopleId.PeopleId
            print("<p>Importing <a href=\"/Person2/{0}\">{1} {2}</a> by matching PeopleId Merge Field".format(
                peopleId, m['merge_fields']['FNAME'], m['merge_fields']['LNAME']))

    if peopleId is None:
        try:
            personSrcSql = model.Content('PersonMatch-NameEmail')
            if "FNAME" in m['merge_fields']:
                personSrcSql = personSrcSql.replace('@first', json.dumps(str(m['merge_fields']['FNAME'])))
            else:
                personSrcSql = personSrcSql.replace('@first', '')
            if "LNAME" in m['merge_fields']:
                personSrcSql = personSrcSql.replace('@last', json.dumps(str(m['merge_fields']['LNAME'])))
            else:
                personSrcSql = personSrcSql.replace('@last', '')
            personSrcSql = personSrcSql.replace('@email', str(m['email_address']).lower())
            # noinspection SqlResolve
            personCntSql = "SELECT COUNT(DISTINCT tt.PeopleId) AS PeopleCnt, COUNT(DISTINCT tt.FamilyId) AS FamilyCnt FROM (" + personSrcSql + ") tt"
        except:
            print("<p>Failed to import {0} - Encoding problem</p>".format(m['email_address']))
            return

        try:
            res = q.QuerySqlTop1(personSrcSql)
            cnt = q.QuerySqlTop1(personCntSql)
        except:
            print("<p>Failed to import {0} - SQL Exception</p>".format(m['email_address']))
            return

        # Person is totally unknown.  If subscribed, create new record.
        if res is None:
            if ("FNAME" in m['merge_fields'] and "LNAME" in m['merge_fields'] and m['merge_fields']['FNAME'] != "" and
                    m['merge_fields']['LNAME'] != "" and m['status'] == 'subscribed'):
                peopleId = model.AddPerson(m['merge_fields']['FNAME'], m['merge_fields']['FNAME'],
                                           m['merge_fields']['LNAME'], m['email_address'])
                print("<p>Imported {0} as new person, {1}</p>".format(m['email_address'], peopleId))
            elif m['status'] == 'subscribed':
                print(
                    "<p>Failed to import {0} - Person not known and insufficient information to create a new Person record.</p>".format(
                        m['email_address']))
                return
            else:
                print(
                    "<p>Failed to import {0} - Person does not match a record.  They are not currently subscribed, and therefore will not be added to TouchPoint.</p>".format(
                        m['email_address']))
                return

        else:
            # If email address is only associated with one family, increase the match score by 1.
            if cnt.FamilyCnt == 1:
                res.score += 1

            # If email address is only associated with one person, increase the match score by 1.
            if cnt.PeopleCnt == 1:
                res.score += 1

            if int(res.score) < 5:
                # The person *probably* exists in the database, but we're not very certain.
                print(
                    "<p>Failed to import {0} - Insufficiently confident about match to <a href=\"/Person2/{1}\">this person</a>. To improve the match, add the person's name to their merge fields on Mailchimp. (Score={2} Families={3} People={4})</p>".format(
                        m['email_address'], res.PeopleId, res.score, cnt.FamilyCnt, cnt.PeopleCnt))
                return

            else:
                # We have a "good enough" match.
                print(
                    "<p>Importing <a href=\"/Person2/{1}\">{0}</a>. (Score={2} Families={3} People={4})".format(
                        m['email_address'], res.PeopleId, res.score, cnt.FamilyCnt, cnt.PeopleCnt))
                peopleId = res.PeopleId

    # Just in care something weird happens
    if peopleId is None:
        print("<p>Failed to import {0} - Unknown error.</p>".format(m['email_address']))
        return

    # Process Adds & Drops

    # Determine Authoritative Source based on Update Dates
    # noinspection SqlResolve
    lastTransSql = """SELECT TOP 1 * FROM [EnrollmentTransaction] 
    WHERE PeopleId=@peopleId AND OrganizationId=@orgId 
    ORDER BY TransactionDate DESC"""
    lastTransaction = q.QuerySqlTop1(
        lastTransSql.replace('@peopleId', str(peopleId)).replace('@orgId', str(l['orgId'])))

    # Person is not--and never has been--a member of the org in TouchPoint
    if lastTransaction is None:
        return SyncPersonMailchimpToTouchPoint(m, l, peopleId)

    mcUpdated = DateTimeFromIso(m['last_changed'][:-6])
    tpUpdated = DateTimeFromIso(lastTransaction.TransactionDate.ToUniversalTime().ToString(
        "yyyy-MM-ddTHH:mm:ss"))  # convert C# DateTime to python datetime

    if mcUpdated > tpUpdated:
        return SyncPersonMailchimpToTouchPoint(m, l, peopleId)
    else:
        update = SyncPersonTouchPointToMailchimp(m['email_address'], l, model.GetPerson(peopleId), lastTransaction)
        if update is not None:
            return update


def SubmitMailchimpUpdate(l):
    print "<h3>Submit Mailchimp Update</h3>"

    updateEndpoint = GetEndpoint(l) + "lists/{0}?skip_merge_validation=false&skip_duplicate_check=false".format(
        l['mcListId'])
    data = {
        'members': updatesForMailchimp[:500],
        'update_existing': True
    }
    
    print RestPost(updateEndpoint, l, data)

    return


def SyncListFromTouchPoint(l, mcEmails):
    ret = []

    print("<h3>Syncing list from TouchPoint</h3>")

    # noinspection SqlResolve
    listSql = '''
    SELECT 
        om.PeopleId,
        p.EmailAddress,
        p.EmailAddress2,
        p.SendEmailAddress1,
        p.SendEmailAddress2,
        COALESCE(p.NickName, p.FirstName) as PreferredName, 
        p.LastName,
        pe.Data as EmailEV
    FROM OrganizationMembers om
        JOIN People p ON om.PeopleId = p.PeopleId
        LEFT JOIN [PeopleExtra] AS pe ON p.PeopleId = pe.PeopleId AND pe.[Field] = 'EmailAddresses'
        WHERE om.OrganizationId = {0}
        '''.format(l['orgId'])

    for m in q.QuerySql(listSql):
        skip = False

        # Skip any email addresses already synced from Mailchimp
        for mcm in mcEmails:
            if mcm['merge_fields'][peopleIdMergeName] == m.PeopleId or \
                    mcm['email_address'] == m.EmailAddress or \
                    mcm['email_address'] == m.EmailAddress2:
                skip = True
                break

        # Skip any email addresses already synced from TouchPoint
        for tpm in ret:
            if tpm['email_address'] == m.EmailAddress or \
                    tpm['email_address'] == m.EmailAddress2:
                skip = True
                break
        if skip:
            continue

        if m.EmailAddress is None and m.EmailAddress2 is not None \
                or m.SendEmailAddress1 is False and m.EmailAddress2 is not None and m.SendEmailAddress2 is not False:
            emailAddress = m.EmailAddress2
        else:
            emailAddress = m.EmailAddress

        update = SyncPersonTouchPointToMailchimp(emailAddress, l, m)
        if update is not None:
            print "<p>This person needs to be imported to Mailchimp: {} {}</p>".format(m.PreferredName, m.LastName)
            EnqueueMailchimpUpdate(l, update)
            ret.append(update)

    return ret


def SyncListFromMailchimp(l):
    print("<h3>Syncing List from Mailchimp</h3>")

    # Import Interest Categories & Interests as Subgroups
    print("<p>Syncing {0} Interests as Subgroups.</p>".format(len(l['subgroups'])))

    offset = 0
    totalItems = 200
    processedEmails = []
    while offset < totalItems:
        membersEndpoint = GetEndpoint(
            l) + "lists/{0}/members/?fields=members.merge_fields,members.email_address,members.unique_email_id,members.interests,members.status,members.last_changed,total_items,members.stats.avg_open_rate&offset={1}&count=200{2}".format(
            l['mcListId'], offset, l['mcLastUpdatedStr'])
        memberObj = RestGet(membersEndpoint, l)
        if offset == 0:
            print(membersEndpoint)
            print("<p>{0} Members to update from Mailchimp.</p>".format(memberObj['total_items']))
        offset += 200
        totalItems = memberObj['total_items']
        for m in memberObj['members']:
            syncResult = SyncMailchimpMember(m, l)
            if syncResult is not None:
                EnqueueMailchimpUpdate(l, syncResult)
                processedEmails.append(syncResult)

    return processedEmails


updatesForMailchimp = []


def EnqueueMailchimpUpdate(l, update):
    global updatesForMailchimp
    updatesForMailchimp.append(update)
    if len(updatesForMailchimp) > 499:
        SubmitMailchimpUpdate(l)
        updatesForMailchimp = updatesForMailchimp[500:]


def SyncLists():
    # noinspection SqlResolve
    listsSql = '''SELECT TOP 1
    o.OrganizationId AS orgId, 
    o.OrganizationName AS name, 
    oe1.Data AS mcLoginId, 
    oe2.Data AS mcListId, 
    oe3.DateValue AS mcLastUpdated,
    oe3.Data as mcLastUpdatedStr
        FROM Organizations o 
        JOIN OrganizationExtra oe1 ON oe1.OrganizationId = o.OrganizationId AND oe1.Field = 'MailchimpLoginId'
        JOIN OrganizationExtra oe2 ON oe2.OrganizationId = o.OrganizationId AND oe2.Field = 'MailchimpListId'
        LEFT JOIN OrganizationExtra oe3 ON oe3.OrganizationId = o.OrganizationId AND oe3.Field = 'MailchimpLastUpdated'
    --ORDER BY RAND()
        '''

    for ls in q.QuerySql(listsSql):
        print "<h2>Syncing {0}</h2>".format(ls.name)

        settingKey = "MailChimpApiKey_{0}".format(ls.mcLoginId)
        l = {
            'orgId': ls.orgId,
            'mcApiKey': model.Setting(settingKey),
            'mcLoginId': ls.mcLoginId,
            'mcListId': ls.mcListId,
            'mcLastUpdatedStr': '',
            'mcLastUpdated': None
        }
        if ls.mcLastUpdated is not None:
            l['mcLastUpdated'] = ls.mcLastUpdated
            l['mcLastUpdatedStr'] = '&since_last_changed=' + ls.mcLastUpdated.ToString("yyyy-MM-dd") + 'T00:00:00+00:00'
        l['subgroups'] = GetSubgroups(l)

        mcEmails = SyncListFromMailchimp(l)

        SyncListFromTouchPoint(l, mcEmails)

        SubmitMailchimpUpdate(l)

        global updatesForMailchimp
        updatesForMailchimp = []  # reset before next loop

        model.AddExtraValueDateOrg(l['orgId'], "MailchimpLastUpdated", date.today() - timedelta(days=1))


def ImportList(l, li, a):
    print("<h2>Importing {0}</h2>".format(l['name']))

    # Search for org based on Mailchimp Extra Value
    # noinspection SqlResolve
    orgSrcSql = """SELECT TOP 1 oe.OrganizationId 
                FROM OrganizationExtra AS oe 
                WHERE oe.Field = 'MailchimpListId' AND oe.Data = '@p1'"""
    qry = q.QuerySqlTop1(orgSrcSql.replace('@p1', str(l['id'])))
    if qry is not None and len(qry) > 0:
        orgId = qry.OrganizationId

    # Search for org based on a.orgId
    elif a['orgId'] is not None and li == 0:
        orgId = a['orgId']  # If this is wrong, the import will fail mostly-gracefully.

    # Create Org
    else:
        orgId = model.AddOrganization("{0} (Mailchimp)".format(l['name']), orgToCopy, False)

    # Set Extra Values on Org
    if model.ExtraValueTextOrg(orgId, "MailchimpListId") == "":
        model.AddExtraValueTextOrg(orgId, "MailchimpListId", l['id'])
    if model.ExtraValueTextOrg(orgId, "MailchimpLoginId") == "":
        model.AddExtraValueTextOrg(orgId, "MailchimpLoginId", a['login_id'])

    print("<p>into <a href=\"/Org/{0}\">Organization {0}</a></p>".format(orgId))


def ImportAccount(a):
    endpoint = GetEndpoint(a)

    # Determine login_id and save API Key to Settings if it isn't there already.
    accountInfo = RestGet(endpoint, a)

    if 'status' in accountInfo:
        print("<h2>The account {0} returned an error: {1}</h2>".format(a['mcUser'], accountInfo['detail']))
        return

    a['login_id'] = accountInfo['login_id']
    settingKey = "MailChimpApiKey_{0}".format(a['login_id'])
    if model.Setting(settingKey) != a['mcApiKey']:
        model.SetSetting(settingKey, a['mcApiKey'])

    # Iterate through the lists
    getListsUrl = endpoint + "lists/?fields=lists.id,lists.name"
    lists = RestGet(getListsUrl, a)
    for li, l in enumerate(lists['lists']):
        ImportList(l, li, a)


def ImportAccounts():
    for a in accounts:
        ImportAccount(a)


if importLists is True or (importLists is None and not model.FromMorningBatch):
    ImportAccounts()
SyncLists()

#