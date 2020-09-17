--roles=Finance
--class=TotalsByFund

DECLARE @ProjectOfMonthFund AS int;

/* If you have a "Project of the Month" fund where different months are identified as separate projects, put the Project of the Month Fund ID here */
SET @ProjectOfMonthFund = 25;

SELECT 
    bd.BundleHeaderId AS BundleId,
    bht.Code as Typ,
    bh.ContributionDate AS BundContribDate,
    c.FundId, 
    cf.FundName AS Name, 
    SUM(c.ContributionAmount) AS Amt,
    cf.FundIncomeFund * 1 AS Account,
    cf.FundIncomeAccount * 1 AS IncomeAccount,
    cf.FundIncomeDept * 1 as Department,
    cf.FundAccountCode * 1 AS Project
FROM Contribution AS c
    LEFT JOIN ContributionFund AS cf on c.FundId = cf.FundId
    LEFT JOIN BundleDetail AS bd on bd.ContributionId = c.ContributionId
    LEFT JOIN BundleHeader AS bh on bd.BundleHeaderId = bh.BundleHeaderId
    LEFT JOIN lookup.BundleHeaderTypes AS bht on bht.Id = bh.BundleHeaderTypeId
WHERE c.FundId <> @ProjectOfMonthFund
    AND bh.ContributionDate between @StartDate AND @EndDate
    AND bh.BundleStatusId = 0
GROUP BY bd.BundleHeaderId, bht.Code, bh.ContributionDate, c.FundId, cf.FundName, cf.FundAccountCode, cf.FundIncomeAccount, cf.FundIncomeDept, cf.FundIncomeFund

UNION ALL

SELECT 
    bd.BundleHeaderId as BundleId,
    bht.Code as Typ,
    bh.ContributionDate AS BundContribDate,
    c.FundId, 
    CONCAT(cf.FundName, ' (', FORMAT(c.ContributionDate, 'Y', 'en-US'), ')' ) AS Name, 
    SUM(c.ContributionAmount) AS Amt,
    cf.FundIncomeFund * 1 as Account,
    cf.FundIncomeAccount * 1 as IncomeAccount,
    cf.FundIncomeDept * 1 as Department,
    MIN(DATEPART(yy, c.ContributionDate) * 100 + DATEPART(mm, c.ContributionDate)) AS Project
FROM Contribution AS c
    LEFT JOIN ContributionFund AS cf on c.FundId = cf.FundId
    LEFT JOIN BundleDetail AS bd on bd.ContributionId = c.ContributionId
    LEFT JOIN BundleHeader AS bh on bd.BundleHeaderId = bh.BundleHeaderId 
    LEFT JOIN lookup.BundleHeaderTypes AS bht on bht.Id = bh.BundleHeaderTypeId 
WHERE c.FundId = @ProjectOfMonthFund
    AND bh.ContributionDate between @StartDate AND @EndDate
    AND bh.BundleStatusId = 0
GROUP BY bd.BundleHeaderId, bht.Code, bh.ContributionDate, c.FundId, FORMAT(c.ContributionDate, 'Y', 'en-US'), cf.FundName, cf.FundAccountCode, cf.FundIncomeAccount, cf.FundIncomeDept, cf.FundIncomeFund

ORDER BY BundContribDate ASC, BundleId ASC, FundId ASC