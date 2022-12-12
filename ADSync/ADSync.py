#API

contactsToSync = "E252AF20-DFAD-46BE-8605-C0692FE499F8"

def FormatDisplayName(p):
    goesBy = p.NickName if p.NickName is not None else p.FirstName
    rescode = p.ResidentCode.Code if p.ResidentCode is not None else p.Family.ResidentCode.Code
    return "{} {} ({} {})".format(goesBy, p.LastName, p.MemberStatus.Code, rescode)


contactCount = q.QueryCount("SavedQuery( SavedQuery='{}' ) = 1[True]".format(contactsToSync))

# TODO allow for more than 1000 contacts

contactList = q.QueryList("SavedQuery( SavedQuery='{}' ) = 1[True]".format(contactsToSync), "name", 10)

Data.contacts = []

for p in contactList:
    ret = {
        "PeopleId": p.PeopleId,
        "displayName": FormatDisplayName(p),
        "firstName": p.NickName if p.NickName is not None else p.FirstName,
        "lastName": p.LastName,
        "email": p.EmailAddress,
        "cellPhone": p.CellPhone,
        "workPhone": p.WorkPhone,
        "homePhone": p.Family.HomePhone
    }
    Data.contacts.append(ret)