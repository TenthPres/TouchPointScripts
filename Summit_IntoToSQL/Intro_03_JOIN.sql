SELECT
    m.MeetingId,
    m.MeetingDate,
    m.MaxCount,
    m.OrganizationId,
    o.OrganizationName
FROM Meetings AS m
         JOIN Organizations AS o ON m.OrganizationId = o.OrganizationId
WHERE m.MeetingDate > DATEADD(DAY, -7, GETDATE())
  AND m.MeetingDate < GETDATE();
