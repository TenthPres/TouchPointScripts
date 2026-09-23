# Pckgd
# Title: Parking Placards
# Description: A module that, together with one of our other web servers, issues family-specific on-street parking permits.
# Updates from: GitHub/TenthPres/TouchPointScripts/ParkingPlacards/ParkingPlacards.py
# Version: 1.0.0
# License: AGPL-3.0
# Author: James at Tenth

import random
import json
from datetime import datetime, timedelta

year = (datetime.now() + timedelta(days=7)).year
evPrefix = "ParkingPlacard_"

WEST_API_TOKEN = model.Setting("WestApiToken", "")

model.Transactional = True

def GetPlacardIdFromPeopleId(peopleId, year = ""):
    evName = evPrefix + str(year)

    sql = """
    SELECT fe.Data FROM People p JOIN FamilyExtra fe ON p.FamilyId = fe.FamilyId WHERE fe.Field LIKE '{0}%' AND p.PeopleId = {1}
    UNION 
    SELECT pe.Data FROM PeopleExtra pe WHERE pe.Field LIKE '{0}%' AND pe.PeopleId = {1}
    """.format(evName, peopleId)

    return q.QuerySqlStr(sql)


def GetPeopleIdFromPlacardId(placardId):
    sql = """
    SELECT p.PeopleId FROM People p JOIN FamilyExtra fe ON p.FamilyId = fe.FamilyId WHERE fe.Field LIKE '{0}%' AND fe.Data = '{1}'
    UNION 
    SELECT pe.PeopleId FROM PeopleExtra pe WHERE pe.Field LIKE '{0}%' AND pe.Data = '{1}'
    """.format(evPrefix, placardId)

    return q.QuerySqlInt(sql)


def GetFamilyIdsFromPlacardId(placardId):
    sql = """
    SELECT fe.FamilyId FROM FamilyExtra fe WHERE fe.Field LIKE '{0}%' AND fe.Data = '{1}'
    UNION 
    SELECT p.FamilyId FROM PeopleExtra pe JOIN People p ON pe.PeopleId = p.PeopleId WHERE pe.Field LIKE '{0}%' AND pe.Data = '{1}' 
    """.format(evPrefix, placardId)

    return q.QuerySqlInts(sql)


def CreateParkingPlacard(year, peopleId, useTemplate = True, accessible = False):

    evName = evPrefix + str(year)
    peopleId = int(peopleId)
    parkingId = GetPlacardIdFromPeopleId(peopleId, year)

    while parkingId == "" or parkingId == None:
        parkingId = ''.join(random.choice('0123456789abcdefhjklmnopqrstvwxyz') for _ in range(12))

        if 0 < GetPeopleIdFromPlacardId(parkingId):
            parkingId = ""
        else:
            model.AddExtraValueText("PeopleId = {}".format(peopleId), evName, parkingId)

    p = model.GetPerson(peopleId)

    d = model.RestPostJson("https://west.tenth.org/files/?prepparking={}".format("content" if useTemplate else "1"), {}, {
        "label": "Issued to the {} Family".format(p.Family.HeadOfHousehold.Name),
        "template": str(year) + ("A" if accessible else ""),
        "parkingId": parkingId,
        "token": WEST_API_TOKEN
    })

    d = json.loads(d)

    if d['status'] == 'error':
        model.Email("PeopleId = 12255", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Parking Placard Exception Context", json.dumps([year, peopleId, useTemplate, parkingId, d]))
        raise Exception(d['message'])

    return "https://west.tenth.org/files/" + d['file']


# Placard request form
if model.Data.InvolvementId == 447:

    #model.Email("PeopleId = 12255", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Registration Info", model.Data.ToString())

    acc = model.Data['885f8e05-2d41-4ad5-81f0-ba77b125a176'] == "Yes"

    url = ""

    if model.Data['53c2b484-d277-4700-908f-a7f869563ba9'] == "kiosk":
        try:
            url = CreateParkingPlacard(year, model.Data.PeopleId, False, acc)

        except Exception as e:
            model.Email("PeopleId = 12255", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Parking Placard Exception", e)

        # document is sent for printing by virtue of being the latest generated from the kiosk, and pops up at the print station.

    try:
        url = CreateParkingPlacard(year, model.Data.PeopleId, True, acc)

        model.Email(str(model.Data.PeopleId), 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Your Parking Placard", """<p>Hi {},</p>
    
<p><a href="{}">Click here to download your household's {} parking placard.</a></p>""".format(model.Data.FirstName, url, year))

    except Exception as e:
        model.Email("PeopleId = 12255", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Parking Placard Exception", e)


# Problem report form
elif model.Data.InvolvementId == 448:
    model.Transactional = True
    fids = map(str, GetFamilyIdsFromPlacardId(model.Data['87b3f0cf-4278-4d5b-a6fe-d88d7b43f073']))
    if len(fids) == 0:
        model.Email("PeopleId = 12255", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Parking Report with Invalid ID", "A report was filed for parking with placard ID {}, but that placard ID doesn't exist.".format(model.Data['87b3f0cf-4278-4d5b-a6fe-d88d7b43f073']))
    else:
        toString = "FamilyId = " + " OR FamilyId = ".join(fids)

        reasonsKey = "46121b8f-f98c-4f87-b7fa-6e2b9b95a051"
        reasons = []

        for key in model.Data.Keys():
            if key.startswith(reasonsKey):
                reasons.append(model.Data.GetValue(key))
        reasons = ", and ".join(reasons).lower()

        message = "Your car has been reported as being parked improperly: {}. You may be ticketed or towed. Please consider moving your car. See tenth.org/parking for the rules.".format(reasons)

        model.Email(toString, 22029, "dbhelp@tenth.org", "Tenth Parking", "You Are Parked Improperly", "{first},\n\n" + message)
        model.SendSms(toString, 1, "Improper Parking Notice", message)

# Admin mode
elif model.Data.id != "" and (model.InOrg(model.UserPeopleId, 125) or model.InOrg(model.UserPeopleId, 61) or model.InOrg(model.UserPeopleId, 374)):
    pid = GetPeopleIdFromPlacardId(model.Data.id)

    if pid > 0:
        print("REDIRECT=https://my.tenth.org/Person2/{}#tab_personal".format(pid))
    else:
        print("Invalid Placard")

# Blue Toolbar
elif q.BlueToolbarCount() > 0:
    for p in q.BlueToolbarReport():
        model.AddMemberToOrg(p.PeopleId, 447)
        url = CreateParkingPlacard(year, p.PeopleId, True, False)
        model.Email(str(p.PeopleId), 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Your Parking Placard", """<p>Hi {},</p>
    
<p><a href="{}">Click here to download your household's {} parking placard.</a></p>""".format(p.NickName or p.FirstName, url, year))

else:
    print("REDIRECT=https://my.tenth.org/OnlineReg/447")

    # reasonsKey = "46121b8f-f98c-4f87-b7fa-6e2b9b95a051"
    # reasons = []

    # for key in model.Data.Keys():
    #     if key.startswith(reasonsKey):
    #         reasons.append(model.Data.GetValue(key))
    # reasons = ", and ".join(reasons).lower()

    # print(reasons)