DECLARE @minTransactionId as int = 17000
DECLARE @paymentOrgId as int = 51

SELECT
    tp.PeopleId,
    p.PreferredName as First,
    p.LastName as Last,
    FORMAT(SUM(t.Amt) * -1, 'C') as Due
FROM [Transaction] t
    LEFT JOIN [TransactionPeople] tp ON t.OriginalId = tp.Id
    LEFT JOIN [People] p ON tp.PeopleId = p.PeopleId
WHERE t.OrgId = @paymentOrgId AND t.Approved = 1 AND t.id > @minTransactionId
GROUP BY tp.PeopleId, p.PreferredName, p.LastName