SELECT
    COUNT(m.MeetingId) AS [count],
    MIN(m.MaxCount) AS [min],
    AVG(m.MaxCount) AS [avg],
    MAX(m.MaxCount) AS [max],
    m.OrganizationId,
    o.OrganizationName
FROM Meetings AS m
         JOIN Organizations AS o ON m.OrganizationId = o.OrganizationId
WHERE m.MeetingDate > DATEADD(MONTH, -1, GETDATE())
  AND m.MeetingDate < GETDATE()
  AND m.DidNotMeet = 0
  AND m.Canceled = 0
  AND o.OrganizationStatusId = 30
  AND m.MaxCount > 0
GROUP BY m.OrganizationId, o.OrganizationName
ORDER BY AVG(m.MaxCount) DESC;
