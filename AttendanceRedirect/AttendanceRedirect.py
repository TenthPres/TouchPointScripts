person = model.GetPerson(model.UserPeopleId)

model.Title = "Communion Attendance"

currentService = q.QuerySqlTop1("""
    DECLARE @LocalTimeZone NVARCHAR(MAX) = (SELECT s.Setting FROM dbo.Setting s WHERE s.Id = 'LocalTimeZone');
	DECLARE @date datetime = CONVERT(DATETIME, SYSDATETIMEOFFSET() AT TIME ZONE @LocalTimeZone);

    SELECT TOP 1 m.MeetingId, m.MeetingDate, m.OrganizationId FROM MeetingExtra me
        LEFT JOIN Meetings m ON me.MeetingId = m.MeetingId
        LEFT JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    WHERE LOWER(Field) = 'communion'
        AND m.MeetingDate < DATEADD(minute, COALESCE(o.EarlyCheckin, 20), @date)
        AND m.MeetingDate > DATEADD(minute, -COALESCE(o.LateCheckin, 100), @date)
    ORDER BY m.MeetingDate DESC
""")

if currentService is None:
    print "There is no communion service happening now.  Please submit your attendance on the paper slips."

else:
    print "REDIRECT={}/OnlineReg/{}".format(model.CmsHost, currentService.OrganizationId)