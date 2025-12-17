-- Pckgd
-- Title: Active Records Over Time
-- Description: Tracks the number of active records per year based on 2025 definition of active.
-- Updates from: GitHub/TenthPres/TouchPointScripts/ActiveRecordsOverTime.sql
-- Author: James at Tenth


WITH FamiliesGiving AS (
    SELECT YEAR(cc.ContributionDate) AS ActivityYear, p.FamilyId
    FROM dbo.Contribution cc WITH (NOLOCK)
             JOIN dbo.People p WITH (NOLOCK) ON p.PeopleId = cc.PeopleId
    WHERE cc.ContributionTypeId IN (1,5,8,9,10,20)
      AND p.IsDeceased = 0
    GROUP BY YEAR(cc.ContributionDate), p.FamilyId
    HAVING COUNT(*) >= 1
),
      PeopleFromGiving AS (
          SELECT fg.ActivityYear, p.PeopleId
          FROM FamiliesGiving fg
                   JOIN dbo.People p WITH (NOLOCK) ON p.FamilyId = fg.FamilyId
          WHERE p.IsDeceased = 0
      ),
      Attenders AS (
          SELECT YEAR(a.MeetingDate) AS ActivityYear, a.PeopleId
          FROM dbo.Attend a WITH (NOLOCK)
                   JOIN dbo.People p WITH (NOLOCK) ON p.PeopleId = a.PeopleId
          WHERE a.AttendanceFlag = 1
            AND p.IsDeceased = 0
          GROUP BY YEAR(a.MeetingDate), a.PeopleId
          HAVING COUNT(*) >= 2
      ),
      LegacyRegCount AS (
          SELECT YEAR(rd.Stamp) AS ActivityYear, rd.UserPeopleId AS PeopleId, COUNT(*) AS rCount
          FROM dbo.RegistrationData rd WITH (NOLOCK)
                   JOIN dbo.People p WITH (NOLOCK) ON rd.UserPeopleId = p.PeopleId
          WHERE rd.UserPeopleId IS NOT NULL AND rd.Completed = 1 AND p.IsDeceased = 0
          GROUP BY YEAR(rd.Stamp), rd.UserPeopleId
      ),
      FormsRegCount AS (
          SELECT YEAR(rp.CompletedDate) AS ActivityYear, rp.PeopleId, COUNT(*) AS rCount
          FROM dbo.RegPeople rp WITH (NOLOCK)
                   JOIN dbo.People p WITH (NOLOCK) ON rp.PeopleId = p.PeopleId
          WHERE rp.PeopleId IS NOT NULL AND rp.[Status] = 2 AND p.IsDeceased = 0
          GROUP BY YEAR(rp.CompletedDate), rp.PeopleId
      ),
      RegistrationCount AS (
          SELECT ActivityYear, PeopleId, SUM(rCount) AS rCount
          FROM (
                   SELECT ActivityYear, PeopleId, rCount FROM LegacyRegCount
                   UNION ALL
                   SELECT ActivityYear, PeopleId, rCount FROM FormsRegCount
               ) r
          GROUP BY ActivityYear, PeopleId
      ),
      Registrants AS (
          SELECT ActivityYear, PeopleId FROM RegistrationCount WHERE rCount >= 2
      ),
      PPL AS (
          SELECT ActivityYear, PeopleId FROM PeopleFromGiving
          UNION ALL
          SELECT ActivityYear, PeopleId FROM Attenders
          UNION ALL
          SELECT ActivityYear, PeopleId FROM Registrants
      ),
      DistinctPPL AS (
          SELECT ActivityYear, PeopleId
          FROM PPL
          GROUP BY ActivityYear, PeopleId
      )
 SELECT ActivityYear, COUNT(*) AS ActiveCount
 FROM DistinctPPL
 GROUP BY ActivityYear
 ORDER BY ActivityYear DESC