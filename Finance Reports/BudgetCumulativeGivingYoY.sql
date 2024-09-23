DECLARE @BudgetJson nvarchar(MAX);

SELECT *
INTO #relevantFunds
FROM FundSetFunds
WHERE FundSetId = 1;


-- Load the budget JSON (assuming it holds data for multiple years and funds)
SET @BudgetJson = (SELECT TOP 1 Body FROM Content WHERE Name = 'Budgets.json');


SELECT c.FundId,
       SUM(c.contributionAmount) AS giving,
       DATEPART(WEEK, c.ContributionDate) as Week,
       DATEPART(YEAR, c.ContributionDate) as Year
INTO #contribs
FROM Contribution c
         JOIN #relevantFunds rf ON c.FundId = rf.FundId
WHERE DATEPART(YEAR, c.ContributionDate) >= 2005
GROUP BY c.FundId, DATEPART(WEEK, c.ContributionDate), DATEPART(YEAR, c.ContributionDate);


SELECT SUM(c.giving) as Giving,
       c.week as Week,
       c.year as Year,
       SUM(CAST(CAST(JSON_VALUE(@BudgetJson, CONCAT('$."', c.year, '"."', c.FundId, '"')) AS MONEY) AS DECIMAL(18,2))) AS Budget
INTO #totalByWeek
FROM #contribs c
GROUP BY c.Week, c.year
ORDER BY c.Year DESC, c.Week DESC;

SELECT
    [Year],
    [Week],
    SUM(Giving) OVER (PARTITION BY [Year] ORDER BY [Week] ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CumGiving,
    Budget
INTO #cumByWeek
FROM #totalByWeek
WHERE Budget IS NOT NULL
;

-- -- This table allows for a proxy of sorts if budget numbers aren't available by using the max given in a year.  Remove the where clause above and uncomment to use.
--
-- SELECT Year,
--     COALESCE(AVG(Budget), MAX(CumGiving)) AS Budgetish
-- INTO #PretendBudget
-- FROM #cumByWeek
-- GROUP BY Year;

-- SELECT cw.Year, cw.Week, cw.CumGiving / pb.Budgetish * 100 as Percentage
-- FROM #cumByWeek cw
-- JOIN #pretendBudget pb ON cw.Year = pb.Year
-- ORDER BY cw.Year, cw.Week;

SELECT cw.Year, cw.Week, cw.CumGiving / cw.Budget * 100 as Percentage
FROM #cumByWeek cw
ORDER BY cw.Year, cw.Week;