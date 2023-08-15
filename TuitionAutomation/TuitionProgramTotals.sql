DECLARE @minTransactionId as int = 17000
DECLARE @paymentOrgId as int = 51

SELECT LEFT(T.MESSAGE, 6) as Program, FORMAT(-SUM(t.amt), 'C') as Billed
FROM [Transaction] t
WHERE t.OrgId = @paymentOrgId
    AND t.amt < 0
    AND t.ID > @minTransactionId
GROUP BY LEFT(T.Message, 6)
ORDER BY LEFT(T.Message, 6)