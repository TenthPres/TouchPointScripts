--roles=Finance

DECLARE @StartDate Date
DECLARE @EndDate Date
DECLARE @PctOfYear decimal(10, 10)

SET @StartDate = DATEADD(yy, DATEDIFF(yy, 0, GETDATE()), 0);
SET @EndDate = DATEADD(yy, DATEDIFF(yy, 0, GETDATE()) + 1, -1);
SET @PctOfYear = DATEPART(dayofyear , GetDate()) * 1.0 / DATEPART(dayofyear , @EndDate);

SELECT cf.FundName AS 'Fund',
	SUM(c.ContributionAmount) AS 'Giving YTD' ,
	CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) * @PctOfYear AS 'Budget YTD',
	SUM(c.ContributionAmount) - CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) * @PctOfYear AS 'Difference',
	(SUM(c.ContributionAmount) - CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) * @PctOfYear) * 100 / (CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) * @PctOfYear)  AS 'Pct'
-- 	CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) AS 'Budget Total',
FROM Contribution c JOIN ContributionFund cf ON c.FundId = cf.FundId
WHERE c.ContributionDate >= @StartDate AND cf.FundStatusId = 1 AND cf.FundCashFund IS NOT NULL
GROUP BY cf.FundName, cf.FundId, cf.FundCashFund
ORDER BY CAST(CAST(cf.FundCashFund AS MONEY) AS DECIMAL(18,2)) DESC
