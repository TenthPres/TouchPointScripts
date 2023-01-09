-- noinspection SqlResolveForFile

SELECT TOP 5 t.PeopleId, t.score, t.Age, t.FamilyId FROM (
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 10 as score FROM People AS p WHERE p.EmailAddress = '@email' AND p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 9 as score FROM People AS p WHERE p.EmailAddress = '@email' AND p.NickName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 9 as score FROM People AS p WHERE p.EmailAddress2 = '@email' AND p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 8 as score FROM People AS p WHERE p.EmailAddress2 = '@email' AND p.NickName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 8 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE '%"@email"%' AND p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 7 as score FROM People AS p WHERE p.EmailAddress = '@email' AND p.FirstName = '@first' AND p.MaidenName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 6 as score FROM People AS p WHERE p.EmailAddress2 = '@email' AND p.FirstName = '@first' AND p.MaidenName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 5 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE '%"@email"%' AND p.FirstName = '@first' AND p.MaidenName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 4 as score FROM People AS p WHERE (p.EmailAddress = '@email' OR p.EmailAddress2 = '@email')
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 3 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE '%"@email"%'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 2 as score FROM People AS p WHERE p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 1 as score FROM People AS p WHERE p.FirstName = '@first' AND p.MaidenName = '@last'
) t 
ORDER BY t.score DESC, t.Age DESC
