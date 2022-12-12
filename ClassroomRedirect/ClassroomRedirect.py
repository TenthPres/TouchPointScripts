from pprint import pprint

model.Title = "Pick a Classroom"

# TODO filter to events where it makes sense to reach out to parents. 

lookoutDays = 2

meetingQ = '''
SELECT TOP 10 o.OrganizationName, m.MeetingId, m.MeetingDate, m.description, o.CanSelfCheckin, * FROM Meetings m
    JOIN Organizations o on m.OrganizationId = o.OrganizationId
    LEFT JOIN Attend a ON m.MeetingId = a.MeetingId AND {0} = a.PeopleId
    LEFT JOIN OrganizationMembers om ON m.OrganizationId = om.OrganizationId AND {0} = om.PeopleId
    LEFT JOIN Lookup.MemberType Lmt ON om.MemberTypeId = Lmt.Id AND 30 > Lmt.AttendanceTypeId -- volunteer (20) or leader (10)
    WHERE ABS(DATEDIFF(dd, getDate()-1, m.MeetingDate)) < {1} AND 
        m.DidNotMeet < 1 AND
        (
            (a.AttendanceFlag = 1) OR -- includes all meetings where person is present.
            (Lmt.AttendanceTypeId > 0) -- includes all meetings where person is a leader.
        )
    ORDER BY ABS(DATEDIFF(mi, getDate()-1, m.MeetingDate)) ASC
'''.format(model.UserPeopleId, lookoutDays)

orgMeetings = q.QuerySql(meetingQ)

orgCnt = len(orgMeetings)

if orgCnt == 0:
    print "<p>There curently aren't any classrooms for you to manage.</p>"
    
else:
    for orgMeeting in orgMeetings:
        link = model.CmsHost
        if orgMeeting.CanSelfCheckin:
            link += "/classroomdashboard/" + str(orgMeeting.MeetingId)
        else:
            link += "/meeting/" + str(orgMeeting.MeetingId)
    
        if orgCnt == 1:
            print "REDIRECT=" + link
            
        else:
            print "<div><a class=\"btn\" style=\"width:100%\" href=\"{}\"><b>{}</b><br />{}</a></div>".format(link, orgMeeting.OrganizationName, orgMeeting.MeetingDate)