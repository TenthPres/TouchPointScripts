-- Pckgd
-- Title: Active Records Over Time
-- Description: Tracks the number of active records per year based on CURRENT definition of active.
-- Updates from: GitHub/TenthPres/TouchPointScripts/ActiveRecordsOverTime.sql
-- Author: James at Tenth

WITH FirstActivity AS (
    SELECT MIN(ActivityDate) AS FirstDate
    FROM (
        SELECT MIN(ContributionDate) AS ActivityDate
        FROM dbo.Contribution

        UNION ALL

        SELECT MIN(MeetingDate)
        FROM dbo.Attend

        UNION ALL

        SELECT MIN(Stamp)
        FROM dbo.RegistrationData

        UNION ALL

        SELECT MIN(CompletedDate)
        FROM dbo.RegPeople
    ) x
),
Years AS (
    SELECT YEAR(FirstDate) AS ActivityYear
    FROM FirstActivity

    UNION ALL

    SELECT ActivityYear + 1
    FROM Years
    WHERE ActivityYear + 1 <= YEAR(GETDATE())
)
SELECT
    y.ActivityYear,
    DATEFROMPARTS(y.ActivityYear, 12, 31) AS AsOfDate,
    COUNT(ar.PeopleId) AS ActiveCount
FROM Years y
CROSS APPLY dbo.ActiveRecords(
    DATEFROMPARTS(y.ActivityYear, 12, 31)
) ar
GROUP BY
    y.ActivityYear
ORDER BY
    y.ActivityYear DESC
OPTION (MAXRECURSION 0);
