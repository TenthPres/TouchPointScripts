SELECT TOP 100 
    ipr.OrganizationName,
    ipr.Stamp,
    ipr.PeopleId,
    ipr.OrganizationId,
    ipr.RegDataId,
    p.name
FROM InProgressRegistrations ipr
    JOIN People p on ipr.PeopleId = p.PeopleId
ORDER BY ipr.Stamp DESC