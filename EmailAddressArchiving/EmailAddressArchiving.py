# This script does not require editing, but knock yourself out if you like.

import json

# Set with the Extra value name to use for the email address array.  Once this script runs once, you probably don't want to change it.
evName = "EmailAddresses"

query = '''(
        EmailAddress2 <> '*@*'
        OR EmailAddress <> '*@*'
        OR HasPeopleExtraField = '$evName_mv'
    )'''.replace("$evName", evName)
    
count = q.QueryCount(query)

print "Saving Email Addresses to Extra Values..."

for p in q.QueryList(query, "PeopleId", count+2): 
    
    addrs = []
    dirty = False
    
    existingEv = model.ExtraValueText(p.PeopleId, evName);
    if existingEv != '':
        addrs = json.loads(existingEv)
        
    movedEv = model.ExtraValueText(p.PeopleId, evName + "_mv");
    if movedEv != '':
        for a in json.loads(movedEv):
            if a.lower() not in addrs:
                addrs.append(a.lower())
                dirty = True
        model.DeleteExtraValue(p.PeopleId, evName + "_mv")
                
    if p.EmailAddress != None and p.EmailAddress.lower() not in addrs:
        addrs.append(p.EmailAddress.lower())
        dirty = True
        
    if p.EmailAddress2 != None and p.EmailAddress2.lower() not in addrs:
        addrs.append(p.EmailAddress2.lower())
        dirty = True

    if dirty:
        model.AddExtraValueText(p.PeopleId, evName, json.dumps(addrs))
        print " updated " + p.Name + "\n"
