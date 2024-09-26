--roles=Finance
--class=TotalsByFund

DECLARE @ProjectOfMonthFund AS int;
DECLARE @RegistrationIncomeFund AS int;

/* If you have a "Project of the Month" fund where different months are identified as separate projects, put the Project of the Month Fund ID here */
SET @ProjectOfMonthFund = 25;

-- Donations, except Project of the Month
SELECT 
    t.BatchRef AS BatchId,
    bht.Code as Typ,
    CONVERT(VARCHAR, c.ContributionDate, 101) AS ContribDate, 
    CONVERT(VARCHAR, t.Settled, 101) as SettleDate, 
    c.FundId, 
    cf.FundName AS Name, 
    SUM(c.ContributionAmount) AS Amt,
    cf.FundAccountCode * 1 AS Project,
    cf.FundIncomeFund * 1 AS Fund, 
    cf.FundIncomeDept * 1 as Department,
    cf.FundIncomeAccount * 1 AS GL,
    COUNT(*) AS Count
FROM Contribution AS c
    LEFT JOIN [Transaction] as t ON c.TranId = t.Id
    LEFT JOIN ContributionFund AS cf on c.FundId = cf.FundId
    LEFT JOIN BundleDetail AS bd on bd.ContributionId = c.ContributionId
    LEFT JOIN BundleHeader AS bh on bd.BundleHeaderId = bh.BundleHeaderId
    LEFT JOIN lookup.BundleHeaderTypes AS bht on bht.Id = bh.BundleHeaderTypeId
WHERE c.FundId <> @ProjectOfMonthFund
    AND c.ContributionTypeId <> 99
    AND c.ContributionDate >= @StartDate AND c.ContributionDate < dateadd(day, 1, @EndDate)
    AND bh.BundleStatusId = 0
GROUP BY t.BatchRef, bht.Code, CONVERT(VARCHAR, c.ContributionDate, 101), CONVERT(VARCHAR, t.Settled, 101), c.FundId, cf.FundName, cf.FundAccountCode, cf.FundIncomeAccount, cf.FundIncomeDept, cf.FundIncomeFund

UNION ALL

-- Registrations
SELECT 
    t.BatchRef AS BatchId,
    CONCAT('R-', bht.Code) as Typ,
    CONVERT(VARCHAR, c.ContributionDate, 101) AS ContribDate,
    CONVERT(VARCHAR, t.Settled, 101) as SettleDate,
    null as fundId, 
    o.OrganizationName AS Name, 
    SUM(c.ContributionAmount) AS Amt,
    TRY_PARSE(SUBSTRING(oe.Data, 1, 4) as int) AS Project,
    TRY_PARSE(SUBSTRING(oe.Data, 6, 3) as int) AS Fund, 
    TRY_PARSE(SUBSTRING(oe.Data, 10, 4) as int) AS Department,
    TRY_PARSE(SUBSTRING(oe.Data, 15, 5) as int) AS GL,
    COUNT(*) AS Count
FROM Contribution AS c
    LEFT JOIN [Transaction] as t ON c.TranId = t.Id
    LEFT JOIN OrganizationExtra as oe ON t.OrgId = oe.OrganizationId AND oe.Field = 'SI Coding'
    LEFT JOIN Organizations as o ON t.OrgId = o.OrganizationId
    LEFT JOIN ContributionFund AS cf on oe.IntValue = cf.FundId
    LEFT JOIN BundleDetail AS bd on bd.ContributionId = c.ContributionId
    LEFT JOIN BundleHeader AS bh on bd.BundleHeaderId = bh.BundleHeaderId
    LEFT JOIN lookup.BundleHeaderTypes AS bht on bht.Id = bh.BundleHeaderTypeId
WHERE c.FundId <> @ProjectOfMonthFund
    AND c.ContributionTypeId = 99
    AND c.ContributionDate >= @StartDate AND c.ContributionDate < dateadd(day, 1, @EndDate)
    AND bh.BundleStatusId = 0
GROUP BY t.BatchRef, bht.Code, CONVERT(VARCHAR, c.ContributionDate, 101), CONVERT(VARCHAR, t.Settled, 101), oe.Data, o.OrganizationName

UNION ALL

-- Project of the Month
SELECT 
    t.BatchRef as BatchId,
    bht.Code as Typ,
    CONVERT(VARCHAR, c.ContributionDate, 101) AS ContribDate,
    CONVERT(VARCHAR, t.Settled, 101) as SettleDate,
    c.FundId, 
    CONCAT(cf.FundName, ' (', FORMAT(c.ContributionDate, 'Y', 'en-US'), ')' ) AS Name, 
    SUM(c.ContributionAmount) AS Amt,
    MIN(DATEPART(yy, c.ContributionDate) * 0 + 6500 + DATEPART(mm, c.ContributionDate)) AS Project,
    cf.FundIncomeFund * 1 AS Fund, 
    cf.FundIncomeDept * 1 as Department,
    cf.FundIncomeAccount * 1 AS GL,
    COUNT(*) AS Count
FROM Contribution AS c
    LEFT JOIN [Transaction] as t ON c.TranId = t.Id
    LEFT JOIN ContributionFund AS cf on c.FundId = cf.FundId
    LEFT JOIN BundleDetail AS bd on bd.ContributionId = c.ContributionId
    LEFT JOIN BundleHeader AS bh on bd.BundleHeaderId = bh.BundleHeaderId 
    LEFT JOIN lookup.BundleHeaderTypes AS bht on bht.Id = bh.BundleHeaderTypeId 
WHERE c.FundId = @ProjectOfMonthFund
    AND c.ContributionDate >= @StartDate AND c.ContributionDate < dateadd(day, 1, @EndDate)
    AND bh.BundleStatusId = 0
GROUP BY t.BatchRef, bht.Code, CONVERT(VARCHAR, c.ContributionDate, 101), CONVERT(VARCHAR, t.Settled, 101), c.FundId, FORMAT(c.ContributionDate, 'Y', 'en-US'), cf.FundName, cf.FundAccountCode, cf.FundIncomeAccount, cf.FundIncomeDept, cf.FundIncomeFund

ORDER BY ContribDate ASC, Typ ASC, BatchId ASC, FundId ASC
