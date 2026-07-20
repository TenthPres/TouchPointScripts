global model, q, Data

dStart = Data.start if Data.start != "" else "2026-01-01"
dEnd   = Data.end   if Data.end   != "" else "2026-07-01"


print("<table>")


print("<tr><td colspan=\"2\"><h2>Health Indicators</h2></td></tr>")

# Worship attendance by time
stat = "Median Worship Attendance"
sql = """

SELECT
    CAST(m.MeetingDate AS TIME) AS ServiceTime,
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
JOIN DivOrg do 
    ON m.OrganizationId = do.OrgId 
    AND do.DivId = 11
WHERE m.MeetingDate >= '{0}'
    AND m.MeetingDate < '{1}'
    AND m.OrganizationId IN (65, 66, 67)
    AND DATEPART(weekday, m.MeetingDate) = 1
    AND CAST(m.MeetingDate AS TIME) IN (
        '09:00:00',
        '11:00:00',
        '14:00:00',
        '18:30:00'
    )
GROUP BY
    CONVERT(DATE, m.MeetingDate),
    CAST(m.MeetingDate AS TIME)
;

SELECT DISTINCT
    ServiceTime,
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count])
                OVER (PARTITION BY ServiceTime),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
ORDER BY ServiceTime;

""".format(dStart, dEnd)
for r in q.QuerySql(sql):
    print("<tr><td>{} {}</td><td>{}</td></tr>".format(stat, r.ServiceTime.ToString().replace(":00", ""), r.MedianCount))



# Median Total Sunday Worship Attendance
stat = "Median Total Sunday Worship Attendance"
sql = """
SELECT 
    CONVERT(DATE, m.MeetingDate) as Date, 
    SUM(m.MaxCount) as [Count]
INTO #stat
FROM Meetings m
JOIN DivOrg do ON m.OrganizationId = do.OrgId AND 11 = do.DivId
WHERE   m.MeetingDate >= '{0}'
    AND m.MeetingDate < '{1}'
    AND m.OrganizationId IN (65, 66, 67) 
    AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY CONVERT(DATE, m.MeetingDate)
;
    

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
worshipTotal = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, worshipTotal))


# Baptisms
stat = "Baptism"
baptismTotal = 0
sql = """
      SELECT BaptismTypeId, COUNT(*) as [Count]
      INTO #stats
      FROM People p
      WHERE p.BaptismDate >= '{0}'
        AND p.BaptismDate < '{1}'
      GROUP BY BaptismTypeId
      ;

      SELECT s.[Count], lbt.Description as [Type]
      FROM #stats s
               JOIN lookup.BaptismType lbt ON s.BaptismTypeId = lbt.Id
      ;

""".format(dStart, dEnd)
for r in q.QuerySql(sql):
    print("<tr><td>{1} {0}</td><td>{2}</td></tr>".format(stat, r.Type, r.Count))
    baptismTotal += r.Count

print("<tr><td>Total Baptisms</td><td>{0}</td></tr>".format(baptismTotal))




# Welcome Cards
stat = "Welcome Cards"
sql = """
SELECT COUNT(DISTINCT tn.AboutPersonId)
FROM TaskNoteKeyword tnk
JOIN TaskNote tn ON tnk.TaskNoteId = tn.TaskNoteId
WHERE tnk.KeywordId = 66
    AND tn.CreatedDate >= '{0}'
    AND tn.CreatedDate < '{1}'
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Membership class registrations
stat = "Membership class registrations"
sql = """
      SELECT COUNT(DISTINCT p.PeopleId)
      FROM dbo.People AS p
      WHERE (EXISTS(
          SELECT NULL AS EMPTY
          FROM dbo.EnrollmentTransaction AS t1
                   INNER JOIN dbo.Organizations AS t2 ON t2.OrganizationId = t1.OrganizationId
          WHERE (t1.OrganizationId = 110) 
            AND (t1.EnrollmentDate >= '{0}') 
            AND (t1.EnrollmentDate < '{1}') 
            AND (t1.TransactionTypeId = 1) 
            AND (t1.PeopleId = p.PeopleId)
      ))
""".format(dStart, dEnd)
membershipClassReg = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, membershipClassReg))



# Membership additions
stat = "Membership Additions"
sql = """
SELECT COUNT(DISTINCT p.PeopleID)
FROM People p
WHERE p.JoinDate >= '{0}'
    AND p.JoinDate < '{1}'
""".format(dStart, dEnd)
membershipAdds = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, membershipAdds))



# Total communicant and noncommunicant members
stat = "Total Communicant and Non-Communicant Members"
# TODO this needs to become a set of status flags that are tracked historically.
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, "TBD."))


# Median Nursery/Children/Youth Sunday Attendance
stat = "Median Nursery/Children/Youth Sunday Attendance"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (17, 19, 20)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Median Adult Bible School participation
stat = "Median Adult Bible School participation"
sql = """

SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (21)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;

""".format(dStart, dEnd)
medianABS = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, medianABS))




# Member of small group
stat = "Member of small group"
sql = """
      SELECT COUNT(DISTINCT p.PeopleId)
      FROM dbo.People AS p
      WHERE (EXISTS(
          SELECT NULL AS EMPTY
          FROM dbo.EnrollmentTransaction AS t1
                   INNER JOIN dbo.Organizations AS t2 ON t2.OrganizationId = t1.OrganizationId
          WHERE (EXISTS(
              SELECT NULL AS EMPTY
              FROM dbo.DivOrg AS t3
              WHERE ((t3.DivId) = 15) AND (t3.OrgId = t2.OrganizationId)
          )) AND ((COALESCE(t1.NextTranChangeDate, GETDATE())) >= '{0} 00:00:00') AND (NOT ((COALESCE(t1.Pending,0)) = 1)) AND (t1.MemberTypeId <> 311) AND ((t1.TransactionDate) <= '{1} 23:59:59') AND (NOT (t1.TransactionStatus = 1)) AND (t1.TransactionTypeId <= 3) AND (t1.PeopleId = p.PeopleId)
      ))
      ;
""".format(dStart, dEnd)
membersOfSmallGroup = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, membersOfSmallGroup))




# Attended small group
stat = "Attended small group (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
JOIN DivOrg do ON a.OrganizationId = do.OrgId AND 15 = do.DivId
WHERE a.AttendanceFlag = 1
AND a.MeetingDate >= '{0}'
AND a.MeetingDate < '{1}'
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Members who have served
stat = "Communicant Members who have served"
sql = """
      SELECT COUNT(*) FROM
          (
              SELECT DISTINCT es.PeopleId AS PeopleId
              FROM EngagementScore es
                       JOIN EngagementScoreTag est ON es.Id = est.EngagementScoreId
              WHERE est.StatusFlagId = 730
                AND es.WeekDate >= '{0}'
                AND es.WeekDate < '{1}'
          ) e
              JOIN People p ON e.PeopleId = p.PeopleId
      WHERE p.MemberStatusId = 10;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Members who have given
stat = "Communicant Members who have given"
sql = """
      SELECT COUNT(*) FROM
          (
              SELECT DISTINCT es.PeopleId AS PeopleId
              FROM EngagementScore es
                       JOIN EngagementScoreTag est ON es.Id = est.EngagementScoreId
              WHERE est.StatusFlagId = 430
                AND es.WeekDate >= DATEADD(DAY, 93, '{0}')
                AND es.WeekDate < '{1}'
          ) e
              JOIN People p ON e.PeopleId = p.PeopleId
      WHERE p.MemberStatusId = 10;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Median 9/11/2 Sunday Worship Attendance / membership
stat = "Median 9+11+2 Sunday Worship Attendance"
sql = """
SELECT 
    CONVERT(DATE, m.MeetingDate) as Date, 
    SUM(m.MaxCount) as [Count]
INTO #stat
FROM Meetings m
JOIN DivOrg do ON m.OrganizationId = do.OrgId AND 11 = do.DivId
WHERE   m.MeetingDate >= '{0}'
    AND m.MeetingDate < '{1}'
    AND m.OrganizationId IN (65, 67) 
    AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY CONVERT(DATE, m.MeetingDate)
;
    

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Members who belong
stat = "Communicant Members who \"belong\""
sql = """
      SELECT COUNT(*) FROM
          (
              SELECT DISTINCT es.PeopleId AS PeopleId
              FROM EngagementScore es
                       JOIN EngagementScoreTag est ON es.Id = est.EngagementScoreId
              WHERE est.StatusFlagId = 241
                AND es.WeekDate >= DATEADD(DAY, 45, '{0}')
                AND es.WeekDate < '{1}'
          ) e
              JOIN People p ON e.PeopleId = p.PeopleId
      WHERE p.MemberStatusId = 10;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



print("<tr><td colspan=\"2\"><h2>KPIs</h2></td></tr>")



stat = "Median Total Sunday Worship Attendance"
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, worshipTotal))





# Total Worship-Related Volunteers
stat = "Total Worship-Related Volunteers (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
JOIN DivOrg do ON a.OrganizationId = do.OrgId AND 51 = do.DivId
WHERE (a.AttendanceFlag = 1 OR Commitment = 1 OR Commitment = 99)
    AND a.MeetingDate >= '{0}'
    AND a.MeetingDate < '{1}'
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))





# Intro to Tenth class attendance
stat = "Intro to Tenth Class Attendance (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
WHERE a.OrganizationId = 508
    AND a.MeetingDate >= '{0}'
    AND a.MeetingDate < '{1}'
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Membership class registrations
stat = "Membership class registrations"
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, membershipClassReg))


# Membership additions
stat = "Membership Additions"
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, membershipAdds))


# Member of small group AND church
stat = "Member of small group (Communicants only)"
sql = """
      SELECT COUNT(DISTINCT p.PeopleId)
      FROM dbo.People AS p
      WHERE (EXISTS(
          SELECT NULL AS EMPTY
          FROM dbo.EnrollmentTransaction AS t1
                   INNER JOIN dbo.Organizations AS t2 ON t2.OrganizationId = t1.OrganizationId
          WHERE (EXISTS(
              SELECT NULL AS EMPTY
              FROM dbo.DivOrg AS t3
              WHERE ((t3.DivId) = 15) AND (t3.OrgId = t2.OrganizationId)
          )) AND ((COALESCE(t1.NextTranChangeDate, GETDATE())) >= '{0} 00:00:00') AND (NOT ((COALESCE(t1.Pending,0)) = 1)) AND (t1.MemberTypeId <> 311) AND ((t1.TransactionDate) <= '{1} 23:59:59') AND (NOT (t1.TransactionStatus = 1)) AND (t1.TransactionTypeId <= 3) AND (t1.PeopleId = p.PeopleId)
      )) AND p.MemberStatusId = 10;
      ;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Median Nursery Sunday Attendance
stat = "Median Nursery Sunday Attendance"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (17)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Median Children's Sunday Attendance
stat = "Median CBS Sunday Attendance"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (19)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Median Youth Sunday Attendance
stat = "Median Youth Sunday Attendance"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (20)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Median TCF Bible School Attendance
stat = "Median TCF Bible School Attendance"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE m.OrganizationId IN (391, 89)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))





# Median Adult Bible School participation
stat = "Median Adult Bible School participation"
sql = """

SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE EXISTS (
    SELECT 1
    FROM DivOrg do
    WHERE do.OrgId = m.OrganizationId
      AND do.DivId IN (21)
)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;

""".format(dStart, dEnd)
medianABS = q.QuerySqlInt(sql)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, medianABS))





# Members who belong
stat = "20s-30s Communicant Members who \"belong\""
sql = """
      SELECT COUNT(*) FROM
          (
              SELECT DISTINCT es.PeopleId AS PeopleId
              FROM EngagementScore es
                       JOIN EngagementScoreTag est ON es.Id = est.EngagementScoreId
              WHERE est.StatusFlagId = 241
                AND es.WeekDate >= DATEADD(DAY, 45, '{0}')
                AND es.WeekDate < '{1}'
          ) e
              JOIN People p ON e.PeopleId = p.PeopleId
      WHERE p.MemberStatusId = 10 
        AND p.Age > 20
        AND p.Age < 40
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))


# Members who belong
stat = "20s-30s Communicant Members"
sql = """
      SELECT COUNT(*) FROM
          People p
      WHERE p.MemberStatusId = 10
        AND p.Age > 20
        AND p.Age < 40 \
      """.format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Attended Christianity Explored
stat = "Attended Christianity Explored (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
JOIN DivOrg do ON a.OrganizationId = do.OrgId AND 50 = do.DivId
WHERE a.AttendanceFlag = 1
AND a.MeetingDate >= '{0}'
AND a.MeetingDate < '{1}'
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))





# Block Party Attendance
stat = "Attended Block Party"
sql = """
  SELECT 
    SUM(m.MaxCount) AS [Count]
INTO #stat
FROM Meetings m
WHERE m.OrganizationId IN (149)
AND m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND DATEPART(weekday, m.MeetingDate) = 1
GROUP BY DATEPART(WEEK, m.MeetingDate), DATEPART(YEAR, m.MeetingDate)
;

SELECT DISTINCT
    CAST(
        ROUND(
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY [Count]) OVER (),
            0
        ) AS INT
    ) AS MedianCount
FROM #stat
;
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))



# Attended Christmas
stat = "Attended Christmas"
sql = """
SELECT SUM(m.MaxCount) AS [Count]
FROM Meetings m
WHERE m.MeetingDate >= '{0}'
AND m.MeetingDate < '{1}'
AND m.OrganizationId IN (140, 411)
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))





# Attended Evangelism Conference
stat = "Attended Evangelism Conference (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
WHERE a.AttendanceFlag = 1
AND a.MeetingDate >= '{0}'
AND a.MeetingDate < '{1}'
AND a.OrganizationId = 136
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))




# Attended Global Conference
stat = "Attended Global Conference (named)"
sql = """
SELECT COUNT(DISTINCT a.PeopleId) AS [Count]
FROM Attend a
WHERE a.AttendanceFlag = 1
AND a.MeetingDate >= '{0}'
AND a.MeetingDate < '{1}'
AND a.OrganizationId IN (112, 423)
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QuerySqlInt(sql)))


# Members on STT
stat = "Members participating in Short Term Trip"
query = """
OrgMemberJoinedAsOf( Div=40[Short Term Trips], StartDate='{0}', EndDate='{1}' ) = 1[True]
AND MemberStatusId = 10[Communicant Member]
""".format(dStart, dEnd)
print("<tr><td>{}</td><td>{}</td></tr>".format(stat, q.QueryCount(query)))





print("</table>")