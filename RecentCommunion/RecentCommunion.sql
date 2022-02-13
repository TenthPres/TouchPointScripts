SELECT DISTINCT a.PeopleId
FROM Attend AS a
JOIN MeetingExtra AS me ON a.MeetingId = me.MeetingId
WHERE a.AttendanceFlag = 1
  AND LOWER(me.Field) = 'communion'
  AND me.data = '1'
  AND MeetingDate >= DATEADD(DAY, -90, CURRENT_TIMESTAMP)
