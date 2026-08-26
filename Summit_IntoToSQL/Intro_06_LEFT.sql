SELECT
    DISTINCT a.PeopleId,
    MIN(a.MeetingDate) AS firstAttends
INTO #FirstAttends
FROM Attend a
WHERE a.AttendanceFlag = 1
GROUP BY a.PeopleId;

SELECT TOP (1000)
    p.PeopleId,
    p.FirstName,
    p.LastName,
    f.FirstAttends
FROM People p
    LEFT JOIN #FirstAttends f ON p.PeopleId = f.PeopleId
WHERE p.BirthYear = 2000
ORDER BY f.FirstAttends;
