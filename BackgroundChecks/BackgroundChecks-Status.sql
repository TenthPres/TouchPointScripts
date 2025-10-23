-- Pckgd
-- Updates from: github/TenthPres/TouchPointScripts/BackgroundChecks/BackgroundChecks-Status.sql

DECLARE @delinquentDate DATE;
SET @delinquentDate = (SELECT CAST(GETDATE() - 10 AS DATE));

SELECT
    tp.PeopleId,
    COALESCE(p.Nickname, p.FirstName) as GoesBy,
    p.LastName,

    CASE WHEN p.Age IS NOT NULL AND p.Age < 18 THEN DATEADD(year, 18, p.BDate) ELSE NULL END AS Minor,

    DATEADD(year, 5, CAHC.ExpDate) as CAHC,
    DATEADD(year, 5, PATCH.ExpDate) as PATCH,
    DATEADD(year, 5, FBI.ExpDate) as FBI,
    DATEADD(year, 5, Aff.ExpDate) as Aff,
    DATEADD(year, 2, LastTraining.TrainingDate) as Training,
    AssignedTraining.TrainingAssignedDate as TrainAssign,
    IIF(t.Name = 'F51', 'Employee', '') as Employee,
    InProgress.InProgressSince as InProgressLastUpdate

INTO #t1

FROM People p
         LEFT JOIN TagPerson tp ON p.PeopleId = tp.PeopleId
         LEFT JOIN Tag t on tp.Id = t.Id

         LEFT JOIN (
    SELECT PeopleId, max(Date) as ExpDate FROM (
                                                   SELECT PeopleId, TRY_CAST(RIGHT(vfv1.Name,CHARINDEX(' ', (REVERSE(vfv1.Name))) - 1) as Date) as Date
                                                   FROM VolunteerForm vfv1 WHERE UPPER(LEFT(vfv1.Name, LEN('CAHC'))) = CONCAT('CAHC', ' ')
                                                   UNION
                                                   SELECT PeopleId, DateValue as Date
                                                   FROM PeopleExtra WHERE Field = 'Background Check: Latest CAHC'
                                               ) CAHCa
    GROUP BY PeopleId
) as CAHC ON p.PeopleId = CAHC.PeopleId

         LEFT JOIN (
    SELECT PeopleId, max(Date) as ExpDate FROM (
                                                   SELECT PeopleId, TRY_CAST(RIGHT(vfv1.Name,CHARINDEX(' ', (REVERSE(vfv1.Name))) - 1) as Date) as Date
                                                   FROM VolunteerForm vfv1 WHERE UPPER(LEFT(vfv1.Name, LEN('PATCH'))) = CONCAT('PATCH', ' ')
                                                   UNION
                                                   SELECT PeopleId, DateValue as Date
                                                   FROM PeopleExtra WHERE Field = 'Background Check: Latest PATCH'
                                               ) PATCHa
    GROUP BY PeopleId
) as PATCH ON p.PeopleId = PATCH.PeopleId

         LEFT JOIN (
    SELECT PeopleId, max(Date) as ExpDate FROM (
                                                   SELECT PeopleId, TRY_CAST(RIGHT(vfv1.Name,CHARINDEX(' ', (REVERSE(vfv1.Name))) - 1) as Date) as Date
                                                   FROM VolunteerForm vfv1 WHERE UPPER(LEFT(vfv1.Name, LEN('FBI'))) = CONCAT('FBI', ' ')
                                                   UNION
                                                   SELECT PeopleId, DateValue as Date
                                                   FROM PeopleExtra WHERE Field = 'Background Check: Latest FBI'
                                               ) FBIa
    GROUP BY PeopleId
) as FBI ON p.PeopleId = FBI.PeopleId

         LEFT JOIN (
    SELECT PeopleId, max(Date) as ExpDate FROM (
                                                   SELECT PeopleId, TRY_CAST(RIGHT(vfv1.Name,CHARINDEX(' ', (REVERSE(vfv1.Name))) - 1) as Date) as Date
                                                   FROM VolunteerForm vfv1 WHERE UPPER(LEFT(vfv1.Name, LEN('Aff'))) = CONCAT('Aff', ' ')
                                                   UNION
                                                   SELECT PeopleId, DateValue as Date
                                                   FROM PeopleExtra WHERE Field = 'ds-Resident Affidavit Date' OR Field = 'ds-FBI Waiver Affidavit Date'
                                               ) Affa
    GROUP BY PeopleId
) as Aff ON p.PeopleId = Aff.PeopleId

         LEFT JOIN (
    SELECT PeopleId, CONVERT(date, MAX(Updated)) as InProgressSince
    FROM BackgroundChecks
    WHERE Updated > DATEADD(month, -3, GETDATE())
      AND ReportTypeID = 1
      AND ApprovalStatus = 'Pending'
    GROUP BY PeopleId
) as InProgress ON p.PeopleId = InProgress.PeopleId

         LEFT JOIN (
    SELECT PeopleId, CONVERT(date, MAX(Updated)) as TrainingDate
    FROM BackgroundChecks
    WHERE ReportTypeID = 3
      AND Score > 80
    GROUP BY PeopleId
) as LastTraining ON p.PeopleId = LastTraining.PeopleId

         LEFT JOIN (
    SELECT PeopleId, CONVERT(date, MAX(Updated)) as TrainingAssignedDate
    FROM BackgroundChecks
    WHERE ReportTypeID = 3
    GROUP BY PeopleId
) as AssignedTraining ON p.PeopleId = AssignedTraining.PeopleId

WHERE t.Name = 'F50' OR t.Name = 'F51';


-- get combined Aff/FBI expiration
SELECT s.*,
       (SELECT MAX(expiration)
        FROM (VALUES
                  (s.FBI),
                  (CASE WHEN s.Employee <> 'Employee' THEN s.Aff ELSE NULL END)
             ) AS ExpirationDates(expiration)
       ) as ActionRequiredA
INTO #t2
FROM #t1 as s;


-- get combined CAHC/PATCH/(FBI/Aff) Expiration and coalesce with delinquents
SELECT s.*,
       (SELECT MIN(expiration)
        FROM (VALUES
                  (COALESCE(s.CAHC, @delinquentDate)),
                  (COALESCE(s.PATCH, @delinquentDate)),
                  (COALESCE(s.ActionRequiredA, @delinquentDate))
             ) AS ExpirationDates(expiration)
       ) as ActionRequiredB
INTO #t3
FROM #t2 as s;


-- combine existing expiration with Minor status
SELECT s.*,
       (SELECT MAX(expiration)
        FROM (VALUES
                  (s.Minor),
                  (s.ActionRequiredB)
             ) AS ExpirationDates(expiration)
       ) as ActionRequired
INTO #t4
FROM #t3 as s;



ALTER TABLE #t4
    DROP COLUMN ActionRequiredA, ActionRequiredB;

SELECT s.*,
       DATEDIFF(day, GetDate(), s.ActionRequired) as DaysToAction,
       IIF(s.ActionRequired > GETDATE(), '', 'Invalid') as Status
-- INTO #status
FROM #t4 as s