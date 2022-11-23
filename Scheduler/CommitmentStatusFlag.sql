DECLARE @InvId Int = 55
DECLARE @Cnt Int = 55
DECLARE @DaysPast Int = 185
DECLARE @DaysFuture Int = 185

SELECT tsmv.PeopleId 
FROM TimeSlotMeetingVolunteers tsmv
    JOIN TimeSlotMeetings tsm ON tsm.TimeSlotMeetingId = tsmv.TimeSlotMeetingId
    JOIN TimeSlotTeams tst ON tsmv.TimeSlotTeamId = tst.TimeSlotTeamId
    JOIN Meetings m on tsm.MeetingId = m.MeetingId
    WHERE tsm.MeetingDateTime > DATEADD(d, -@DaysPast, GETDATE()) AND tsm.MeetingDateTime < DATEADD(d, @DaysFuture, GETDATE()) AND tsmv.IsActive = 1
        AND OrganizationId = @InvId
GROUP BY tsmv.PeopleId HAVING COUNT(*) >= @Cnt