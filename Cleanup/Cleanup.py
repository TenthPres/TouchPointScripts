#Role=Admin

global q

# Active Involvements with Past End Dates
print("<h2>Active Involvements with Past End Dates</h2>")
print("<p>Each of these involvements has an end date in the past, but is listed as Active.  Either the dates need to "
      "be updated, or the status should be changed to Inactive.</p>")

print("<ul>")
sql = """SELECT TOP 100 OrganizationId, OrganizationName 
    FROM Organizations WHERE LastMeetingDate < GETDATE() AND LastMeetingDate IS NOT NULL AND OrganizationStatusId = 30"""
for i in q.QuerySql(sql, {}):
    print("<li><a href=\"/Org/{0}\">{1} ({0})</a></li>".format(i.OrganizationId, i.OrganizationName))
print("</ul>")


# Main Fellowships w/o Attendance
print("<h2>Active Main Fellowship Involvements without attendance</h2>")
print("<p>Each of these involvements has not reported attendance within the last 30 days.</p>")

print("<ul>")
sql = """
WITH meetingsCte AS ( -- Select Meetings that match what we want to see
    SELECT m.OrganizationId, m.MeetingDate
    FROM Meetings m 
    WHERE m.MeetingDate > DATEADD(day, -30, GETDATE())
        AND m.MeetingDate < GETDATE()
        AND m.NumPresent > 3
)
SELECT o.OrganizationId, o.OrganizationName FROM Organizations o 
    LEFT JOIN meetingsCte m ON o.OrganizationId = m.OrganizationId
    WHERE (o.LastMeetingDate > DATEADD(day, -30, GETDATE()) OR o.LastMeetingDate IS NULL) 
    AND o.OrganizationStatusId = 30
    AND o.IsBibleFellowshipOrg = 1
    AND m.MeetingDate IS NULL
"""
for i in q.QuerySql(sql, {}):
    print("<li><a href=\"/Org/{0}\">{1} ({0})</a></li>".format(i.OrganizationId, i.OrganizationName))
print("</ul>")