SELECT s.*,
       IIF(s.Minor >= GETDATE() OR (
           s.CAHC >= GETDATE() AND
           s.PATCH >= GETDATE() AND (
               s.FBI > GETDATE() OR (
                   s.Aff >= GETDATE() AND
                   s.Employee <> 'Employee'
                   )
               )
           ), '', 'Invalid') as Status

FROM (
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
             IIF(t.Name = 'F51', 'Employee', '') as Employee,
             InProgress.InProgressSince as InProgressLastUpdate

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

         WHERE t.Name = 'F50' OR t.Name = 'F51'

     ) s