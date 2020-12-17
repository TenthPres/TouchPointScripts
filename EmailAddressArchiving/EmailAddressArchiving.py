# This script does not require editing, but knock yourself out if you like.

import json
from pprint import pprint

# Set with the Extra value name to use for the email address array.  Once this script runs once, you probably don't want to change it.
evName = "EmailAddresses"

query = '''(
        EmailAddress2 <> ''
        OR EmailAddress <> ''
        OR HasPeopleExtraField = '$evName_mv'
    '''.replace("$evName", evName)
    
count = q.QueryCount(query)

for p in q.QueryList(query, "PeopleId"): # TODO add count option when PR 1205 is released. 
    print "<h2>" + p.Name + "</h2>"
    
    addrs = []
    dirty = False
    
    existingEv = model.ExtraValueText(p.PeopleId, evName);
    if existingEv != '':
        addrs = json.loads(existingEv)
        
    movedEv = model.ExtraValueText(p.PeopleId, evName + "_mv");
    if existingEv != '':
        for a in json.loads(existingEv):
            if a.lower() not in addrs:
                addrs.append(a.lower())
        model.DeleteExtraValue(p.PeopleId, evName + "_mv")
                
    if p.EmailAddress != None and p.EmailAddress.lower() not in addrs:
        addrs.append(p.EmailAddress.lower())
        
    if p.EmailAddress2 != None and p.EmailAddress2.lower() not in addrs:
        addrs.append(p.EmailAddress2.lower())
        
    model.AddExtraValueText(p.PeopleId, evName, json.dumps(addrs))
    
    pprint(json.dumps(addrs))