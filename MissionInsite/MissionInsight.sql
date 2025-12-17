-- Pckgd
-- Title: Blue Toolbar Mission Insight Export
-- Description: Outputs people information in the format expected by MissionInsight import.  MissionInsight is a third party application from ACS Technologies.
-- Updates from: GitHub/TenthPres/TouchPointScripts/MissionInsight/MissionInsight.sql
-- Author: James at Tenth

SELECT
                        p.PeopleId as ClientId,
                        COALESCE(p.NickName, p.FirstName) as FirstName,
                        p.LastName,
                        p.PrimaryAddress AS Address1,
                        p.PrimaryAddress2 AS Address2,
                        p.PrimaryCity AS City,
                        p.PrimaryState AS State,
                        IIF(
                                LEN(p.PrimaryZip) > 5 AND SUBSTRING(p.PrimaryZip, 6, 1) <> '-',
                                LEFT(p.PrimaryZip, 5) + '-' + SUBSTRING(p.PrimaryZip, 6, LEN(p.PrimaryZip) - 5),
                                p.PrimaryZip
                        ) AS ZipCode,
                        CASE
                            WHEN LEN(COALESCE(p.CellPhone, f.HomePhone)) = 11 AND LEFT(COALESCE(p.CellPhone, f.HomePhone), 1) = '1' THEN SUBSTRING(COALESCE(p.CellPhone, f.HomePhone), 2, 10)
                            WHEN LEN(COALESCE(p.CellPhone, f.HomePhone)) = 10 THEN COALESCE(p.CellPhone, f.HomePhone)
                            ELSE NULL
                            END AS Phone,
                        COALESCE(p.EmailAddress, p.EmailAddress2) AS Email,
                        null as 'Year Entered K', -- TODO
    'Member Status' = case p.MemberStatusId
                          WHEN 10 THEN 1
                          WHEN 12 THEN 1
                          WHEN 15 THEN 3
                          WHEN 20 THEN 5
                          WHEN 30 THEN 2
                          WHEN 35 THEN 4
                          WHEN 40 THEN 5
                          WHEN 50 THEN null
                          ELSE null
                            END,
    'Member By Means' = case p.JoinCodeId
                            WHEN 0 THEN null
                            WHEN 10 THEN 1
                            WHEN 20 THEN null
                            WHEN 30 THEN 4
                            WHEN 40 THEN 1
                            WHEN 50 THEN 2
                            WHEN 60 THEN 1
                            WHEN 70 THEN 3
                            WHEN 80 THEN 1
                            WHEN 90 THEN 4
                            WHEN 100 THEN 4
                            ELSE null
                            END,
                        (SELECT MIN(a.MeetingDate) FROM Attend a WHERE a.PeopleId = p.PeopleId) AS 'First Attend Date',
                        p.JoinDate AS 'Member Date',
                        p.bDate AS 'Birthdate',
                        p.baptismDate as 'Baptism Date'
FROM People p
         JOIN dbo.TagPerson tp ON tp.PeopleId = p. PeopleId
         LEFT JOIN Families f ON p.FamilyId = f.FamilyId
WHERE p.MemberStatusId <> 50 -- exclude just added
  AND p.PrimaryAddress IS NOT NULL
  AND p.PrimaryAddress <> ''
  AND p.PrimaryState IS NOT NULL
  AND p.PrimaryState <> ''
  AND tp.ID = @BlueToolbarTagId