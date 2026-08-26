SELECT
    *
FROM Meetings
WHERE MeetingDate > DATEADD(DAY, -7, GETDATE())
  AND MeetingDate < GETDATE();