SELECT TOP 10 * FROM (
    SELECT mtg.MeetingDate as Date, 'Attended' as Action, org_att.OrganizationName as Detail, org_att.LeaderName as Leader 
    FROM Attend att 
        LEFT JOIN Meetings mtg on att.MeetingId = mtg.MeetingId
        LEFT JOIN Organizations org_att on mtg.OrganizationId = org_att.OrganizationId
    WHERE att.PeopleId = @p1 AND att.AttendanceFlag = 1
    
    UNION
    
    SELECT oen.EnrollmentDate as Date, 'Joined' as Action, org_en.OrganizationName as Detail, org_en.LeaderName as Leader
    FROM OrganizationMembers oen
        LEFT JOIN Organizations org_en ON oen.OrganizationId = org_en.OrganizationId
    WHERE oen.PeopleId = @p1
    
    UNION
    
    SELECT max(er.Dt) as Date, 'Opened Email' as Action, eq.Subject as Detail, eq.FromName as Leader 
    FROM EmailResponses er 
        LEFT JOIN EmailQueue eq on er.EmailQueueId = eq.Id
    WHERE er.PeopleId = @p1
    GROUP BY eq.Id, eq.Subject, eq.FromName -- if a single email was opened multiple times, only the most recent time will be lsited.
) t
ORDER BY Date DESC