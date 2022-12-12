from datetime import datetime
month = datetime.today().month

print """
<style>

tbody {
    border-top: 3px solid #aaa;
}
tr {
    border-bottom: 1px solid #aaa;
}

td, th {
    padding: .5em;
}

</style>

"""

print "<table>"

print """
<thead>
<tr>
<th>First</th>
<th>Last</th>
<th>Email Addr / Birthday (Age)</th>
<th>List?</th>
<th>Cell Number</th>
<th>Present?</th>
</tr>
</thead>
"""

currentOrg = model.CurrentOrgId or Data.CurrentOrgId
pp = None
for p in q.BlueToolbarReport('name'):
    print "<tbody>"
    print "<tr>"
    print "<td>{}</td>".format(p.FirstName)
    print "<td>{}</td>".format(p.LastName)
    print "<td>{}</td>".format(p.EmailAddress)
    print ("<td>&#x2714;</td>" if model.InOrg(p.PeopleId, currentOrg) else "<td></td>")
    print "<td>{}</td>".format(p.CellPhone)
    print "<td></td>"
    print "</tr>"
    
    if pp is not None and pp.FamilyId != p.FamilyId:
        for fp in p.Family.People:
            if fp.PeopleId == p.PeopleId:
                continue
            if fp.PositionInFamilyId != 30:
                continue
            
            print "<tr>"
            print "<td>{}</td>".format(fp.FirstName)
            print "<td>{}</td>".format(fp.LastName)
            if fp.BirthMonth == month:
                print "<td style=\"background: #ff0\">{}/{} ({})</td>".format(fp.BirthMonth, fp.BirthDay, fp.Age)
            else:
                print "<td>{}/{} ({})</td>".format(fp.BirthMonth, fp.BirthDay, fp.Age)
            print "<td></td>"
            print "<td>{}</td>".format(fp.CellPhone)
            print "<td></td>"
            print "</tr>"
    
    pp = p
    
    print "</tbody>"

print "</table>"