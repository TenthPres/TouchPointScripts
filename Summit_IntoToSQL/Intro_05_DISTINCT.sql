SELECT
    DISTINCT a.PeopleId,
             MAX(a.MeetingDate) AS MostRecent
FROM Attend a
WHERE a.OrganizationId = 502
  AND a.AttendanceFlag = 1
  AND a.MeetingDate > DATEADD(MONTH, -6, GETDATE())
GROUP BY a.PeopleId;

-- SELECT
--     DISTINCT a.PeopleId,
--              MIN(a.MeetingDate) AS firstAttends
-- INTO #FirstAttends
-- FROM Attend a
-- GROUP BY a.PeopleId;
