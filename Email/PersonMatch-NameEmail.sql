-- noinspection SqlResolveForFile

DECLARE @emailV varchar(80) = '@email';
DECLARE @emailLike varchar(84) = '%"@email"%';

SELECT TOP 5 t.PeopleId, t.score, t.Age, t.FamilyId FROM (
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 10 as score FROM People AS p WHERE p.EmailAddress = @emailV AND p.FirstName = '@first' AND p.LastName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 9 as score FROM People AS p WHERE p.EmailAddress2 = @emailV AND p.FirstName = '@first' AND p.LastName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 8 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE @emailLike AND p.FirstName = '@first' AND p.LastName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 7 as score FROM People AS p WHERE p.EmailAddress = @emailV AND p.FirstName = '@first' AND p.MaidenName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 6 as score FROM People AS p WHERE p.EmailAddress2 = @emailV AND p.FirstName = '@first' AND p.MaidenName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 5 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE @emailLike AND p.FirstName = '@first' AND p.MaidenName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 4 as score FROM People AS p WHERE (p.EmailAddress = @emailV OR p.EmailAddress2 = @emailV)
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 3 as score FROM [PeopleExtra] AS pe JOIN [People] AS p ON pe.PeopleId = p.PeopleId WHERE pe.[Field] = 'EmailAddresses' AND pe.Data LIKE @emailLike
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 2 as score FROM People AS p WHERE p.FirstName = '@firstV' AND p.LastName = '@last'
    UNION
    SELECT TOP 5 p.PeopleId, p.Age, p.FamilyId, 1 as score FROM People AS p WHERE p.FirstName = '@firstV' AND p.MaidenName = '@last'
) t
ORDER BY t.score DESC, t.Age DESC



/*  Used Previously
 SELECT TOP 1 PeopleId, FamilyId, score FROM (
SELECT p.PeopleId, p.Age, p.FamilyId, 10 as score FROM People AS p WHERE p.EmailAddress = '@email'AND p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 9 as score FROM People AS p WHERE p.EmailAddress2 = '@email' AND p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 8 as score FROM People AS p WHERE p.EmailAddress = '@email' AND p.FirstName = '@first' AND p.MaidenName = '@last'
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 7 as score FROM People AS p WHERE p.EmailAddress2 = '@email' AND p.FirstName = '@first' AND p.MaidenName = '@last'
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 6 as score FROM People AS p WHERE (p.EmailAddress = '@email' OR p.EmailAddress2 = '@email')
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 4 as score FROM People AS p WHERE p.FirstName = '@first' AND p.LastName = '@last'
UNION
SELECT p.PeopleId, p.Age, p.FamilyId, 3 as score FROM People AS p WHERE p.FirstName = '@first' AND p.MaidenName = '@last'
) t
ORDER BY t.score DESC, t.Age DESC
 */