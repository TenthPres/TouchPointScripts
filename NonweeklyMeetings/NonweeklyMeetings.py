from datetime import datetime
from pprint import pprint
from math import floor

OrgsWithNonWeekly = q.QuerySql("""SELECT o.organizationId orgId, o.organizationName orgName FROM Organizations o WHERE o.NotWeekly = 1 AND o.OrganizationStatusId = 30 AND (o.FirstMeetingDate IS NULL OR o.FirstMeetingDate < GETDATE()) AND (o.LastMeetingDate IS NULL OR o.LastMeetingDate > GETDATE())""")

for o in OrgsWithNonWeekly:
    freqs = q.QuerySql("SELECT SUBSTRING(Field, 11, 1000) freq FROM OrganizationExtra WHERE OrganizationId = {} AND Field LIKE 'Frequency:%' AND BitValue = 1".format(o.orgId))
    
    scheds = q.QuerySql("SELECT NextMeetingDate nextDate FROM OrgSchedule WHERE OrganizationId = {}".format(o.orgId))
    
    for f in freqs:
        for s in scheds:
            week = 1 + floor((s.nextDate.Day - 1) / 7)
            addMeeting = False
            
            if f.freq == 'Every Other':
                exists = q.QuerySqlInt("SELECT COUNT(*) FROM Meetings WHERE OrganizationId = {} AND MeetingDate > DATEADD(dd, -13, '{}')".format(o.orgId, s.nextDate))
                if exists < 1:
                    addMeeting = True
            
            elif f.freq == 'First' and week == 1:
                addMeeting = True
                
            elif f.freq == 'Second' and week == 2:
                addMeeting = True
                
            elif f.freq == 'Third' and week == 3:
                addMeeting = True
            
            elif f.freq == 'Fourth' and week == 4:
                addMeeting = True
                
            elif f.freq == 'Fifth' and week == 5:
                addMeeting = True
                
            else:
                pass
                
            if addMeeting:
                mtgId = model.GetMeetingIdByDateTime(o.orgId, s.nextDate, True)  # If the meeting already exists, nothing happens.
                
                print "Meeting {} created or found for {} ({})\n<br><br>".format(mtgId, o.orgName, f.freq)
