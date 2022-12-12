#Roles=Admin
# MailChimpImport

from pprint import pprint
from random import randint
import base64
import json
import time
import sys



# The "lists" list should be a list of the ConstantContact lists you wish to import.  
# The ccListId is the List ID used for 
# The mcApiKey is the API Key from the Mailchimp UI (See Touchpoint's instructions for how to get that).  The -usX suffix must be 
#               included on the end, as that indicates which server should be used for the API. 
# The orgId is one of the following: 
#   - a number - The org Id number of the org you want current subscribers to be imported into. If you only have one list in the 
#               MailChimp account, this will be fine. 
#   - None -    This creates a new org for the purpose.  It will give the org an extra value that links it to the MailChimp list, 
#               so that if you run the import again, it won't create a new list again. 
#
#               If you have multiple lists in a single account, either leave it as None to have all new orgs created, or add the 
#               extra value "MailChimpListId" as the 10-digit hex ID Mailchimp uses as a list ID.

lists = [
    {
        "ccListId": "YOUR LIST ID",
        "orgId": 62
    }
]


API_KEY = "YOUR API KEY"
API_SECRET = "YOUR API SECRET"


# Great job. That's all the setup you need to do. 

###################################################################################################################################

idCustomFieldId = None
contactsToRemoveFromList = []
currentListId = None
handledPids = []

def getAuthHeaders():
    return {
        'Authorization': "Basic " + base64.b64encode(API_KEY + ":" + API_SECRET),
        'Content-Type': "application/x-www-form-urlencoded"
    }
        
def getBearerHeaders():
    return {
        'Authorization': 'Bearer ' + model.Setting("ConstantContactAccessToken", "")
    }
        
def parseTokens(tokens):
    tokens = json.loads(tokens)
    
    if "access_token" in tokens:
        model.SetSetting("ConstantContactAccessToken", tokens['access_token'])
        return True
        
    else:
        model.SetSetting("ConstantContactAccessToken", "")
        return False
        
        
def refreshTokens():
    tokens = model.RestPost("https://authz.constantcontact.com/oauth2/default/v1/token?refresh_token=" + model.Setting("ConstantContactAccessToken", none) + "grant_type=refresh_token", getAuthHeaders(), "")
    return parseTokens(tokens)
    
def handleContactRemovals(force = False):
    global contactsToRemoveFromList
    global currentListId
    
    if (force and len(contactsToRemoveFromList) > 0) or len(contactsToRemoveFromList) > 100:
        d = {
            "source": {
                "contact_ids": contactsToRemoveFromList
            },
            "list_ids": [currentListId]
        }
        
        print "<h2>Handle Removals:</h2>"
        print "<pre>"
        pprint(d)
        print "</pre>"
        
        r = model.RestPostJson("https://api.cc.email/v3/activities/remove_list_memberships", getBearerHeaders(), d)
        # not doing anything with the response, because it doesn't really matter. 
        
        contactsToRemoveFromList = []
    
def importContactToOrg(c, orgId):
    peopleId = None
    p = None
    
    global idCustomFieldId
    global handledPids
    
    # Find List member in TouchPoint
    if c.has_key('custom_fields'):
        for cf in c['custom_fields']:
            if (cf['custom_field_id'] == idCustomFieldId):
                peopleId = int(cf['value'])
                prsn = model.GetPerson(peopleId)
                if prsn is not None:
                    p = prsn
                    break
                
    if p is None:
        personSrcSql = model.Content('PersonMatch-NameEmail')
        if ("first_name" in c):
            personSrcSql = personSrcSql.replace('@first', json.dumps(str(c['first_name'])))
        else:
            personSrcSql = personSrcSql.replace('@first', '')
        if ("last_name" in c):
            personSrcSql = personSrcSql.replace('@last', json.dumps(str(c['last_name'])))
        else:
            personSrcSql = personSrcSql.replace('@last', '')
        personSrcSql = personSrcSql.replace('@email', str(c['email_address']['address']))
        
        try:
            res = q.QuerySqlTop1(personSrcSql)
        except:
            print("<p>Failed to import {0} - SQL Exception</p>".format(c['contact_id']))
            return False
        
        if (res == None or len(res) < 1):
            # Person is totally unknown, so we'll add if we have a full name. 
            if ("first_name" in c and "last_name" in c and c['first_name'] != "" and c['last_name'] != ""):
                peopleId = model.AddPerson(c['first_name'], None, c['last_name'], c['email_address']['address'])
            else:
                print("<p>Failed to import {0} - Person not known and insufficient information to create a new Person record</p>".format(c['email_address']['address']))
                return False
        
        elif int(res.score) < 5:
            # The person *probably* exists in the database, but we're not very certain. 
            print("<p>Failed to import {0} - Insufficiently Confident about match to <a href=\"/Person2/{1}\">this person</a>.</p>".format(c['email_address']['address'], res.PeopleId))
            return
        
        else:
            # We have a "good enough" match.
            peopleId = res.PeopleId
    
        p = model.GetPerson(peopleId)
        
    if p is None:
        print("<p>Failed to import {0} - GetPerson failed</p>".format(c['email_address']['address']))
        return
    
    handledPids.append(p.PeopleId)
    
    if not model.InOrg(p.PeopleId, orgId):
        if p.IsDeceased or q.QuerySqlInt("SELECT COUNT(*) FROM InvolvementPrevious({}, 1) WHERE OrganizationId = {}".format(peopleId, orgId)) > 0:
            # Person has previously been an org member but isn't now, drop from CC
            print "Person to remove from list: {}".format(p.PeopleId)
            contactsToRemoveFromList.append(c['contact_id'])
            handleContactRemovals()
        else:
            # Add Person to Org
            print "Person to add to org: {}".format(p.PeopleId)
            model.AddMemberToOrg(p.PeopleId, orgId)
        
    return True
    
def checkTokens():
    # This request gets a list of allowed sending emails as a quick test to see if we're authenticated.  
    data = json.loads(model.RestGet("https://api.cc.email/v3/account/emails", getBearerHeaders()))
    
    return isinstance(data, list)

def parseImport(data, orgId):
    for c in data['contacts']:
        if not importContactToOrg(c, orgId):
            print "<h2>Importing this contact failed</h2>"
            print "<pre>"
            pprint(c)
            print "</pre>"
    
    if ("_links" in data) and ("next" in data['_links']):
        data = json.loads(model.RestGet("https://api.cc.email" + data['_links']['next']['href'], getBearerHeaders()))
        parseImport(data, orgId)
        
def exportOthers(orgId):
    global handledPids
    for om in q.QuerySql("SELECT om.PeopleId, om.EnrollmentDate, p.EmailAddress, p.EmailAddress2 FROM OrganizationMembers om JOIN People p ON om.PeopleId = p.PeopleId WHERE om.OrganizationId = {} AND om.Pending = 0 ORDER BY PeopleId".format(orgId)):
        if om.PeopleId not in handledPids:
            #p = model.GetPerson(om.PeopleId)
            print "{} is not included yet. {}</br>".format(om.EmailAddress, om.EnrollmentDate)
            # Determine if contact exists and/or is unsubscribed.  If unsubscribed, remove from org...?
            
    handledPids = []
    
def importLists():
    customFields = json.loads(model.RestGet("https://api.cc.email/v3/contact_custom_fields", getBearerHeaders()))
    global idCustomFieldId
    global currentListId
    
    for cf in customFields['custom_fields']:
        if cf['name'] == 'tp_id':
            idCustomFieldId = cf['custom_field_id']
            break
    
    for li in lists:
        data = json.loads(model.RestGet("https://api.cc.email/v3/contacts?status=all&lists=" + li['ccListId'] + "&include=custom_fields&limit=500&include_count=false", getBearerHeaders()))
        
        currentListId = li['ccListId']
        
        parseImport(data, li['orgId'])
        handleContactRemovals(True)
        
        exportOthers(li['orgId'])
    
    
if hasattr(Data, "code") and Data.code != "":
    tokens = model.RestPost("https://authz.constantcontact.com/oauth2/default/v1/token?code=" + Data.code + "&redirect_uri=" + model.CmsHost + "/PyScript/ConstantContact&grant_type=authorization_code", getAuthHeaders(), "")
    
    parseTokens(tokens)
    
    time.sleep(10)
    print "REDIRECT=" + model.CmsHost + "/PyScript/ConstantContact"
    
else:
    accessToken = model.Setting("ConstantContactAccessToken", "")
    
    if (accessToken == "" or not checkTokens()):
        print "<a href=\"https://authz.constantcontact.com/oauth2/default/v1/authorize?client_id=" + API_KEY + "&redirect_uri=" + model.CmsHost + "/PyScript/ConstantContact&response_type=code&state=" + "{}".format(randint(0, 99999)) + "&scope=contact_data+account_read\">Get API Token</a>"
    
    else:
        importLists()
        print "Success"
        pass