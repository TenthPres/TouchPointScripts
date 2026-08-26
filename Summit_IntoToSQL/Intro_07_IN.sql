SELECT DISTINCT OrgId
INTO #targetOrgs
FROM DivOrg
WHERE DivId IN (17, 19);

SELECT TOP (1000)
    p.PeopleId,
    COALESCE(p.NickName, p.FirstName) as GoesBy,
    p.LastName,
    p.EmailAddress,
    p.CellPhone,
    o.OrganizationId,
    o.OrganizationName AS InvolvementName,
    mt.Description AS LeaderType
FROM OrganizationMembers om
         JOIN #targetOrgs t ON om.OrganizationId = t.OrgId
         JOIN People p ON om.PeopleId = p.PeopleId
         JOIN Organizations o ON om.OrganizationId = o.OrganizationId
         JOIN lookup.MemberType mt ON om.MemberTypeId = mt.Id
WHERE om.MemberTypeId IN (140, 150, 160)
  AND o.OrganizationStatusId = 30
ORDER BY p.LastName, o.OrganizationName;
