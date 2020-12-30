# This script does not require editing, but you can if you really, really, want.

import json

# Set with the Extra value name to use for the email address array.  Once this script runs once, you probably don't want to change it.
evName = "EmailAddresses"

sql = '''
    SELECT p.PeopleId FROM [People] p LEFT JOIN [PeopleExtra] pe ON pe.PeopleId = p.PeopleId AND pe.Field = '$evName'
        WHERE Data NOT LIKE '%"' + LOWER(EmailAddress) + '"%'
            OR Data NOT LIKE '%"' + LOWER(EmailAddress2) + '"%'
    UNION
    SELECT pe.PeopleId FROM [PeopleExtra] pe
        WHERE pe.Field = '$evName_mv'
    UNION
    SELECT pe.PeopleId FROM [PeopleExtra] pe
        WHERE pe.Field = '$evName_mv_mv'
    '''.replace("$evName", evName)

query = "peopleids='{}'".format(q.QuerySqlPeopleIds(sql))
    
count = q.QueryCount(query)

print "Saving Email Addresses to Extra Values..."

for p in q.QueryList(query, "PeopleId", count): 
    
    addrs = []
    dirty = False
    
    # Load existing EV, if it exists.
    existingEv = model.ExtraValueText(p.PeopleId, evName);
    if existingEv != '':
        addrs = json.loads(existingEv)
    
    # Merged once
    movedEv = model.ExtraValueText(p.PeopleId, evName + "_mv");
    if movedEv != '':
        for a in json.loads(movedEv):
            if a.lower() not in addrs:
                addrs.append(a.lower())
                dirty = True
        model.DeleteExtraValue(p.PeopleId, evName + "_mv")
        
    # Merged twice
    movedEv = model.ExtraValueText(p.PeopleId, evName + "_mv_mv");
    if movedEv != '':
        for a in json.loads(movedEv):
            if a.lower() not in addrs:
                addrs.append(a.lower())
                dirty = True
        model.DeleteExtraValue(p.PeopleId, evName + "_mv_mv")
    
    # Primary Address
    if p.EmailAddress != None and p.EmailAddress.lower() not in addrs:
        addrs.append(p.EmailAddress.lower())
        dirty = True
    
    # Secondary Address
    if p.EmailAddress2 != None and p.EmailAddress2.lower() not in addrs:
        addrs.append(p.EmailAddress2.lower())
        dirty = True
        
    # Update
    if dirty:
        model.AddExtraValueText(p.PeopleId, evName, json.dumps(addrs))
        print " updated " + p.Name + "\n"