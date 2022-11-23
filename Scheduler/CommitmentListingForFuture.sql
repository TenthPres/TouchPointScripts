DECLARE @InvId Int = 55
DECLARE @Days Int = 180

SELECT 
    COALESCE(p.NickName, p.FirstName) as First, 
    p.LastName as Last, 
    tsm.MeetingDateTime as DateTime, 
    tst.TeamName
FROM TimeSlotMeetingVolunteers tsmv
    JOIN TimeSlotMeetings tsm ON tsm.TimeSlotMeetingId = tsmv.TimeSlotMeetingId
    JOIN TimeSlotTeams tst ON tsmv.TimeSlotTeamId = tst.TimeSlotTeamId
    JOIN People p ON tsmv.PeopleId = p.PeopleId
    JOIN Meetings m on tsm.MeetingId = m.MeetingId
    WHERE tsm.MeetingDateTime > GETDATE() AND tsm.MeetingDateTime < DATEADD(d, @Days, GETDATE()) AND tsmv.IsActive = 1
        AND OrganizationId = @InvId
ORDER BY tsm.MeetingDateTime, tsmv.TimeSlotTeamId