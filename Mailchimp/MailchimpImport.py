#Roles=Admin
# MailchimpImport

import json
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
#               If you have multiple lists in a single account, either leave it as None to have all new orgs created, or add the 
#               extra value "MailChimpListId" as the 10-digit hex ID Mailchimp uses as a list ID.

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

# Set a minimum open rate.  If a user opens less than this rate, they won't be imported, and will be unsubscribed from the list.  
minOpenRate = 0.01

# Set a minimum retention period.  If a user has been subscribed for this number of days or less, they won't be unsubscribed, even if
# their open rates are below the minOpenRate
minRetentionDays = 45

# Great job. That's all the setup you need to do. 

###################################################################################################################################


headers = { 'content-type': 'application/json' }

skips = 0


def RestGet(url, account):
    returnvalue = model.RestGet(url, headers, account['mcUser'], account['mcApiKey'])
    return json.loads(returnvalue)
    
def GetEndpoint(a):
    return "https://{0}.api.mailchimp.com/3.0/".format(a['mcApiKey'].split('-')[1])
    
def GetSubgroups(l, a):
    interestCategoriesEndpoint = GetEndpoint(a) + "lists/{0}/interest-categories?fields=categories.id,categories.title".format(l['id'])
    interestCategories = RestGet(interestCategoriesEndpoint, a)['categories']
    
    subgroups = {}
    
    for ic in interestCategories:
        interestsEndpoint = GetEndpoint(a) + "lists/{0}/interest-categories/{1}/interests?fields=interests.id,interests.name".format(l['id'], ic['id'])
        interests = RestGet(interestsEndpoint, a)['interests']
        
        for i in interests:
            subgroups[i['id']] = "{0} - {1}".format(ic['title'], i['name'])
    
    return subgroups
    

def ImportListMemberToOrg(m, orgId, subgroups):
    global skips
    
    # Verify that they are subscribed
    if m['status'] != 'subscribed':
        skips+=1
        return
    
    # Verify that their open rate justifies subscription
    if m['stats']['avg_open_rate'] < minOpenRate:
        skips+=1
        return
    
    # Find List member in TouchPoint
    if "PEOPLEID" in m['merge_fields']:
        peopleId = m['merge_fields']['PEOPLEID']  # TODO: verify that this ID corresponds to a current person. 
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
        personSrcSql = personSrcSql.replace('@email', str(m['email_address']))
        
        try:
            res = q.QuerySqlTop1(personSrcSql)
        except:
            print("<p>Failed to import {0} - SQL Exception</p>".format(m['email_address']))
            return
        
        if (res == None or len(res) < 1):
            # Person is totally unknown, so we'll add if we have a full name. 
            if ("FNAME" in m['merge_fields'] and "LNAME" in m['merge_fields'] and m['merge_fields']['FNAME'] != "" and m['merge_fields']['LNAME'] != ""):
                peopleId = model.AddPerson(m['merge_fields']['FNAME'], m['merge_fields']['FNAME'], m['merge_fields']['LNAME'], m['email_address'])
            else:
                print("<p>Failed to import {0} - Person not known and insufficient information to create a new Person record</p>".format(m['email_address']))
                return
        
        elif int(res.score) < 5:
            # The person *probably* exists in the database, but we're not very certain. 
            print("<p>Failed to import {0} - Insufficiently Confident about match to <a href=\"/Person2/{1}\">this person</a>.</p>".format(m['email_address'], res.PeopleId))
            return
        
        else:
            # We have a "good enough" match.
            peopleId = res.PeopleId
    
    if not model.InOrg(peopleId, orgId):
        model.AddMemberToOrg(peopleId, orgId)
        
    if 'interests' in m:
        for sgid in m['interests']:
            sgn = subgroups[sgid]
            if m['interests'][sgid] == False and model.InSubGroup(peopleId, orgId, sgn):
                model.RemoveSubGroup(peopleId, orgId, sgn)
            elif m['interests'][sgid] == True and not model.InSubGroup(peopleId, orgId, sgn):
                model.AddSubGroup(peopleId, orgId, sgn)
            
        
    
    
def ImportList(l, li, a):  # l = list | li = listIndex | a = account from config
    print("<h2>Importing {0}</h2>".format(l['name']))

    # Search for org based on MailChimp Extra Value
    orgSrcSql = "SELECT TOP 1 oe.OrganizationId FROM OrganizationExtra AS oe WHERE oe.Field = 'MailChimpListId' AND oe.Data = '@p1'"
    qry = q.QuerySqlTop1(orgSrcSql.replace('@p1', str(l['id'])))
    if (qry != None and len(qry) > 0):
        orgId = qry.OrganizationId

    # Search for org based on a.orgId
    elif (a['orgId'] != None):
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
    print(" with {0} Interests as Subgroups.</p>".format(len(subgroups)))
    
    # Import Members (Finally!)
    offset = 0
    totalItems = 200
    while (offset < totalItems):
        membersEndpoint = GetEndpoint(a) + "lists/{0}/members/?fields=members.merge_fields,members.email_address,members.unique_email_id,members.interests,members.status,members.last_changed,total_items,members.stats.avg_open_rate&offset={1}&count=200".format(l['id'], offset)
        memberObj = RestGet(membersEndpoint, a)
        offset += 200
        totalItems = memberObj['total_items']
        for m in memberObj['members']:
            ImportListMemberToOrg(m, orgId, subgroups)
    

def ImportAccount(a):
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
        ImportList(l, li, a)


def ImportAccounts():
    for a in accounts:
        ImportAccount(a)
    
    
ImportAccounts()