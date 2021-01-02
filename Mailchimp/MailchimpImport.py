#Roles=Admin
# MailChimpImport

import json
from datetime import datetime
from pprint import pprint


# The accounts list should be a list of the MailChimp accounts you wish to import.  
# The mcUser is the username (or email) you use to sign in to Mailchimp. 
# The mcApiKey is the API Key from the Mailchimp UI (See Touchpoint's instructions for how to get that).  The -usX suffix must be 
#               included on teh end, as that indicates which server should be used for the API. 
# The orgId is one of the following: 
#   - a number - The org Id number of the org you want current subscribers to be imported into. If you only have one list in the 
#               MailChimp account, this will be fine. 
#   - None -    This creates a new org for the purpose.  It will give the org an extra value that links it to the MailChimp list, 
#               so that if you run the import again, it won't create a new list again. 
#
#               If you have multiple lists in a single account, set orgId as None to have all new orgs created, or add the extra 
#               value "MailChimpListId" as the 10-digit hex ID Mailchimp uses as a list ID.

accounts = [
    {
        "mcUser": "xxxxxxxxxxxx",
        "mcApiKey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-usX",
        "orgId": None
    },
    {
        "mcUser": "xxxxxxxxxxxx",
        "mcApiKey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-usX",
        "orgId": None
    }
]


# Give an OrgId to use as a template for new orgs that may be created with the import. 
orgToCopy = 78

# Mailchimp Interest Categories and Interests will be imported into TouchPoint as Sub-Groups and kept synchronized.  By default, the
# subgroups will be named in the format "Category Title :: Interest Name".  Change this setting to change the separator.  The 
# separator needs to be distinct.  That is, it needs to be a pattern that you probably don't have in subgroups otherwise. To prevent 
# Categories from being synchronized, set this to None. (As a value, not as a string.) 
categoryInterestSeparator = " :: "

# The TouchPoint PeopleId will be saved into a Merge field in TouchPoint.  This allows future syncs to run more efficiently. If you
# would like to change the name of the merge field, do so here.  You probably do not need to change this. 
peopleIdMergeName = "TP_pid"


# Great job. That's all the setup you need to do. 

###################################################################################################################################


headers = { 'content-type': 'application/json' }

skips = 0

def DateTimeFromIso(dtStr):  # TODO Replace with native functions if TouchPoint upgrades Python to 3.2+  Or, use a C# method instead. 
    # parse the date/time part
    return datetime.strptime(dtStr, '%Y-%m-%dT%H:%M:%S') # Assumes UTC!

def RestGet(url, account):
    returnvalue = model.RestGet(url, headers, account['mcUser'], account['mcApiKey'])
    return json.loads(returnvalue)
    
def GetEndpoint(a):
    return "https://{0}.api.mailchimp.com/3.0/".format(a['mcApiKey'].split('-')[1])
    
def GetSubgroups(l, a):
    if categoryInterestSeparator == None:
        return {}
    
    interestCategoriesEndpoint = GetEndpoint(a) + "lists/{0}/interest-categories?fields=categories.id,categories.title".format(l['id'])
    interestCategories = RestGet(interestCategoriesEndpoint, a)['categories']
    
    subgroups = {}
    
    for ic in interestCategories:
        interestsEndpoint = GetEndpoint(a) + "lists/{0}/interest-categories/{1}/interests?fields=interests.id,interests.name".format(l['id'], ic['id'])
        interests = RestGet(interestsEndpoint, a)['interests']
        
        for i in interests:
            subgroups[i['id']] = "{0} {1} {2}".format(ic['title'], categoryInterestSeparator, i['name'])
    
    return subgroups

def SyncPersonMailchimpToTouchPoint(m, orgId, peopleId, subgroups):
    """
    # if m['status'] == 'subscribed':
    #     # Add, if not already.
    #     if not model.InOrg(peopleId, orgId):  # TODO test speed against using Transaction status. 
    #         model.AddMemberToOrg(peopleId, orgId)

    #     # Update subgroups
    #     if 'interests' in m and categoryInterestSeparator != None:
    #         for sgid in m['interests']:
    #             sgn = subgroups[sgid]
    #             if m['interests'][sgid] == False and model.InSubGroup(peopleId, orgId, sgn):
    #                 model.RemoveSubGroup(peopleId, orgId, sgn)
    #             elif m['interests'][sgid] == True and not model.InSubGroup(peopleId, orgId, sgn):
    #                 model.AddSubGroup(peopleId, orgId, sgn)
                    
    # elif m['status'] == 'unsubscribed' or m['status'] == 'archived':
    #     # Drop, if not already.
    #     if model.InOrg(peopleId, orgId):
    #         model.DropOrgMember(peopleId, orgId)
            
    # elif m['status'] == 'cleaned':
    #     # Drop, if not already.
    #     if model.InOrg(peopleId, orgId):
    #         model.DropOrgMember(peopleId, orgId)
            
        # TODO Remove email address from any profile that has it. 
        
    # Contacts who have the Mailchimp status 'pending' are imported as People records, but are not added to the Organization.
    """
    if not peopleIdMergeName in m['merge_fields']:
        return {
            'merge_fields': {
                peopleIdMergeName: peopleId
                },
            'email_address': m['email_address'],
            'status': m['status']
        }
    return None

def SyncPersonTouchPointToMailchimp(m, orgId, peopleId, subgroups, transaction):
    p = model.GetPerson(peopleId)
    
    ret = {
        'merge_fields': {
            peopleIdMergeName: peopleId,
            'FNAME': p.PreferredName,  # TODO: only update when different???? Only when subscribed???
            'LNAME': p.LastName
            },
        'email_address': m['email_address'],  # TODO: differentiate when m is not provided. 
        'status': None
    }
    
    if (transaction.TransactionTypeId == 1 and transaction.Pending == False) or transaction.TransactionTypeId == 3:  # TransactionTypeId == 1 => "Join" , 3 => "Change", else => "Drop",
        ret['status'] = 'subscribed'
        
        # Update Subgroups/Interests
        if categoryInterestSeparator != None and len(subgroups) > 0:
            interestSql = "SELECT mt.Name FROM OrgMemMemTags ommt LEFT JOIN MemberTags mt ON ommt.MemberTagId = mt.Id WHERE ommt.OrgId=@orgId AND ommt.PeopleId=@peopleId AND mt.Name LIKE '%@separator%'"
            interestSql = interestSql.replace('@peopleId', str(peopleId)).replace('@orgId', str(orgId)).replace('@separator', categoryInterestSeparator)
            ret['interests'] = subgroups
            for intSql in q.QuerySql(interestSql):
                for k, intNameList in ret['interests'].items():
                    if intSql.Name == intNameList:
                        ret['interests'][k] = True
            for k, v in ret['interests'].items():
                if v != True:
                    ret['interests'][k] = False
                
    else :
        ret['status'] = 'unsubscribed'
        
    return ret

def SyncMailchimpMember(m, orgId, subgroups):
    global skips
    
    peopleId = None
    
    ## Find or Create Mailchimp Member in TouchPoint
    if peopleIdMergeName in m['merge_fields']:
        peopleId = m['merge_fields'][peopleIdMergeName]  # TODO: verify that this ID corresponds to a current person. 
    else:
        personSrcSql = model.Content('PersonMatcher-NameEmail')
        if ("FNAME" in m['merge_fields']):
            personSrcSql = personSrcSql.replace('@first', json.dumps(str(m['merge_fields']['FNAME'])))
        else:
            personSrcSql = personSrcSql.replace('@first', '')
        if ("LNAME" in m['merge_fields']):
            personSrcSql = personSrcSql.replace('@last', json.dumps(str(m['merge_fields']['LNAME'])))
        else:
            personSrcSql = personSrcSql.replace('@last', '')
        personSrcSql = personSrcSql.replace('@email', str(m['email_address']).lower())
        personCntSql = "SELECT COUNT(DISTINCT tt.PeopleId) AS PeopleCnt, COUNT(DISTINCT tt.FamilyId) AS FamilyCnt FROM (" + personSrcSql + ") tt"
        
        try:
            res = q.QuerySqlTop1(personSrcSql)
            cnt = q.QuerySqlTop1(personCntSql)
        except:
            print("<p>Failed to import {0} - SQL Exception</p>".format(m['email_address']))
            return
        
        # Person is totally unknown.  If subnscribed, create new record. 
        if (res == None): 
            if ("FNAME" in m['merge_fields'] and "LNAME" in m['merge_fields'] and m['merge_fields']['FNAME'] != "" and m['merge_fields']['LNAME'] != "" and m['status'] == 'subscribed'):
# todo UNCOMMENT                peopleId = model.AddPerson(m['merge_fields']['FNAME'], m['merge_fields']['FNAME'], m['merge_fields']['LNAME'], m['email_address'])
                print("<p>Failed to import {0} - Person record creation is disabled.</p>".format(m['email_address']))    
                return # todo REMOVE
            elif m['status'] == 'subscribed':
                print("<p>Failed to import {0} - Person not known and insufficient information to create a new Person record.</p>".format(m['email_address']))
                return
            else:
                print("<p>Failed to import {0} - Person does not match a record.  They are not currently subscribed, and will therefore not be added to TouchPoint.</p>".format(m['email_address']))
                return
        
        # If email address is only associated with one family, increase the match score by 1. 
        if cnt.FamilyCnt == 1:
            res.score+=1
        
        # If email address is only associated with one person, increase the match score by 1. 
        if cnt.PeopleCnt == 1:
            res.score+=1
        
        if int(res.score) < 5:
            # The person *probably* exists in the database, but we're not very certain. 
            print("<p>Failed to import {0} - Insufficiently confident about match to <a href=\"/Person2/{1}\">this person</a>. To improve the match, add the person's name to their merge fields on Mailchimp. (Score={2} Families={3} People={4})</p>".format(m['email_address'], res.PeopleId, res.score, cnt.FamilyCnt, cnt.PeopleCnt))
            return
        
        else:
            # We have a "good enough" match.
            peopleId = res.PeopleId

    # Just in care something weird happens
    if peopleId == None:
        print("<p>Failed to import {0} - Unknown error.</p>".format(m['email_address']))
        return
            
    ## Process Adds & Drops
    
    # Determine Authoritatifve Source based on Update Dates
    lastTransSql = "SELECT TOP 1 * FROM [EnrollmentTransaction] WHERE PeopleId=@peopleId AND OrganizationId=@orgId ORDER BY TransactionDate DESC"
    lastTransaction = q.QuerySqlTop1(lastTransSql.replace('@peopleId', str(peopleId)).replace('@orgId', str(orgId)))
    
    # Person is not--and never has been--a member of the org in TouchPoint
    if (lastTransaction == None):
        return SyncPersonMailchimpToTouchPoint(m, orgId, peopleId, subgroups)
    
    mcUpdated = DateTimeFromIso(m['last_changed'][:-6])
    tpUpdated = DateTimeFromIso(lastTransaction.TransactionDate.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss")) # convert C# DateTime to python datetime
    
    if (mcUpdated > tpUpdated):
        return SyncPersonMailchimpToTouchPoint(m, orgId, peopleId, subgroups)
    else:
        return SyncPersonTouchPointToMailchimp(m, orgId, peopleId, subgroups, lastTransaction)
    
    
def SyncList(l, li, a):  # l = list | li = listIndex | a = account from config
    print("<h2>Importing {0}</h2>".format(l['name']))

    # Search for org based on MailChimp Extra Value
    orgSrcSql = "SELECT TOP 1 oe.OrganizationId FROM OrganizationExtra AS oe WHERE oe.Field = 'MailChimpListId' AND oe.Data = '@p1'"
    qry = q.QuerySqlTop1(orgSrcSql.replace('@p1', str(l['id'])))
    if (qry != None and len(qry) > 0):
        orgId = qry.OrganizationId

    # Search for org based on a.orgId
    elif (a['orgId'] != None and li == 0):
        orgId = a['orgId']  # If this is wrong, the import will fail mostly-gracefully. 
    
    # Create Org
    else:
        orgId = model.AddOrganization("{0} (MailChimp)".format(l['name']), orgToCopy, False)
        
    # Set Extra Values on Org
    if (model.ExtraValueTextOrg(orgId, "MailChimpListId") == ""):
        model.AddExtraValueTextOrg(orgId, "MailChimpListId", l['id'])
    if (model.ExtraValueTextOrg(orgId, "MailChimpLoginId") == ""):
        model.AddExtraValueTextOrg(orgId, "MailChimpLoginId", a['login_id'])
        
    print("<p>into <a href=\"/Org/{0}\">Organization {0}</a>".format(orgId))
    
    # Import Interest Categories & Interests as Subgroups
    subgroups = GetSubgroups(l, a)
    print(" with {0} Interests as Subgroups.  ".format(len(subgroups)))
    
    # Import Members (Finally!)
    offset = 0
    totalItems = 200
    updatesForMailchimp = []
    while (offset < totalItems):
        membersEndpoint = GetEndpoint(a) + "lists/{0}/members/?fields=members.merge_fields,members.email_address,members.unique_email_id,members.interests,members.status,members.last_changed,total_items,members.stats.avg_open_rate&offset={1}&count=200&since_last_changed=2020-01-01T00:00:00+00:00".format(l['id'], offset)
        memberObj = RestGet(membersEndpoint, a)
        if offset == 0:
            print(" {0} Members to update.</p>".format(memberObj['total_items']))
        offset += 200
        totalItems = memberObj['total_items']
        for m in memberObj['members']:
            syncResult = SyncMailchimpMember(m, orgId, subgroups)
            if not syncResult == None:
                updatesForMailchimp.append(syncResult)
                
    pprint (updatesForMailchimp) # TODO submit updates to Mailchimp.

def SyncAccount(a):
    endpoint = GetEndpoint(a)
    
    # Determine login_id and save API Key to Settings if it isn't there already. 
    accountInfo = RestGet(endpoint, a)
    
    if 'status' in accountInfo:
        print("<h2>The account {0} returned an error: {1}</h2>".format(a['mcUser'], accountInfo['detail']))
        return
    
    a['login_id'] = accountInfo['login_id']
    settingKey = "MailChimpApiKey_{0}".format(a['login_id'])
    if (model.Setting(settingKey) != a['mcApiKey']):
        model.SetSetting(settingKey, a['mcApiKey'])
    
    # Iterate through the lists
    getListsUrl = endpoint + "lists/?fields=lists.id,lists.name"
    lists = RestGet(getListsUrl, a)
    for li, l in enumerate(lists['lists']):
        SyncList(l, li, a)


def SyncAccounts():
    for a in accounts:
        SyncAccount(a)
    
    
SyncAccounts()