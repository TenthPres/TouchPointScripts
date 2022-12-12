sql = """
SELECT o.OrganizationId 
FROM Organizations o
LEFT JOIN lookup.OrganizationType ot 
    ON o.OrganizationTypeId = ot.Id
WHERE ot.Code = 'CHILD'
"""

for iid in q.QuerySqlInts(sql):
    print "<p>Updating Involvement {}</p>".format(iid)
    model.AddExtraValueBoolOrg(iid, "ministrysafeonlabel", True)
    model.AddExtraValueBoolOrg(iid, "backgroundcheckonlabel", True)