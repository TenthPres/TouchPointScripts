--Roles=Admin

SELECT TOP 100 
    cl.Created as [Timestamp],
    CONCAT(COALESCE(u.NickName, u.FirstName), ' ', u.LastName) as [Changed by],
    CONCAT(COALESCE(s.NickName, s.FirstName), ' ', s.LastName) as Subject,
    s.PeopleId as [PeopleId],
    cl.Field as [Section],
    cd.Field as [Field],
    COALESCE(cl.Before, cd.Before) as [Before],
    COALESCE(cl.After, cd.After) as [After],
    cd.Id as [Change ID]
FROM ChangeLog cl 
    LEFT JOIN People u on cl.UserPeopleId = u.PeopleId 
    LEFT JOIN People s on cl.PeopleId = s.PeopleId 
    FULL JOIN ChangeDetails cd on cl.Id = cd.Id

ORDER BY [Created] DESC