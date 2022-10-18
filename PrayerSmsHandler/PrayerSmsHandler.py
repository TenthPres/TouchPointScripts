#API
#
# If your looking to adopt this script, scroll down to the section "Variables to Update"
#
# Variable reference:
# Data.ToNumber the Twilio phone number used to send the original message
# Data.ToGroupId the Twilio Group ID in Touchpoint (Should you need to use this, the information is stored in dbo.SMSGroups. You can see the ID for a group with the simple SQL command SELECT * FROM dbo.SMSGroups.)
# Data.FromNumber the user’s number from which the reply was sent
# Data.Message the contents of the reply (in this case, the Reply Word)
# Data.PeopleId the sender’s TouchPoint people ID
# Data.Name the sender’s full name
# Data.First the sender’s first name

import json

# ################### #
# Variables to Update #
# ################### #

# When the person sending the text can't be identified, the prayer request will be assigned to a generic "annonymous" person.  Put that Person's PeopleId here:
unknownUserPid = 29120

# When the person sending the text can't be identified, the reply will ask for their name.  When the name is submitted, a task will be created for someone on
# your staff to go back and reassign the original task, and clean up the sender's profile to include their number. This is likely a "New People Manager" but
# could be any one person with access.  Put their PeopleId here.  
peopleManagerPid = 12255

# What keywords do you want associated with the prayer requests? Put the *IDs* (not the names) of those keywords here.  There is no easy way to find the keyword
# IDs.  See the README for how-to. 
prayerKeywords = [7, 59]


# All Done! 

# ######################

states = json.loads(model.TextContent('SmsStates-AS.json') or "{}")

if Data.FromNumber not in states:
    noteBody = Data.Message
    
    if Data.PeopleId is None:
        noteBody += """
        
        Submitted by {}""".format(Data.FromNumber)
        
        Data.PeopleId = unknownUserPid
        
        model.CreateTaskNote(Data.PeopleId, Data.PeopleId, None, None, True, None, noteBody, None, prayerKeywords)
        print "Your prayer request has been submitted.  Thank you.  \nWe don't have your email address on file.  Please reply with your name."
        
        states[Data.FromNumber] = "unknownNumber"
        model.WriteContent("SmsStates-AS.json", json.dumps(states))
        
    else:
        model.CreateTaskNote(Data.PeopleId, Data.PeopleId, None, None, True, None, noteBody, None, prayerKeywords)
        print "Your prayer request has been submitted.  Thank you."


# Probably responding to a request for a name. 
else:
    
    noteBody = "**Unrecognized Incoming SMS**  {}".format(Data.Body)
    
    if Data.PeopleId == 0:
        Data.PeopleId = unknownUserPid
        
    states.pop(Data.FromNumber)
    model.WriteContent("SmsStates-AS.json", json.dumps(states))
    
    model.CreateTaskNote(peopleManagerPid, Data.PeopleId, None, None, False, None, noteBody, None, [])
    

# pprint(Data)