DECLARE @Year Int;
DECLARE @Month Int;
DECLARE @Today DateTime;
DECLARE @TodayPY DateTime;
DECLARE @StartDate DateTime;
DECLARE @StartDatePY DateTime;
DECLARE @StartDateMo Date;
DECLARE @PctOfYear decimal(11, 10);
DECLARE @MonthName varchar(18);
DECLARE @BudgetJson nvarchar(MAX);

SET @Year = CAST(@p1 AS INT);


IF @Year = 1 
    SET @Today = getdate();
ELSE IF @Year > 1000
    SET @Today = DATEFROMPARTS(@Year, 12, 31);
ELSE
    SET @Today = DATEADD(DAY, 1-DATEPART(WEEKDAY, getdate()), getdate()); -- roll back to Sunday

SET @Today = DATEADD(SECOND, -1, DATEADD(DAY, DATEDIFF(DAY, 0, @Today) + 1, 0)) -- Set to 11:59:59pm
SET @TodayPY = DATEADD(YEAR, -1, @Today)
SET @Year = DATEPART(yyyy, @Today)
SET @Month = DATEPART(MONTH, @Today)
SET @MonthName = DATENAME(MONTH , @Today);
SET @StartDate = DATEFROMPARTS(@Year, 01, 01);
SET @StartDatePY = DATEADD(YEAR, -1, @StartDate)
SET @StartDateMo = DATEFROMPARTS(@Year, @Month, 01)
SET @PctOfYear = (DATEPART(dayofyear, @Today)) * 1.0 / (DATEPART(dayofyear, DATEFROMPARTS(@Year, 12, 31)));
SET @BudgetJson = (SELECT TOP 1 Body FROM Content WHERE Name = 'Budgets.json');

SELECT c.FundId, 
    SUM(c.contributionAmount) AS giving, 
    DATEPART(MONTH, c.ContributionDate) as Month,
    DATEPART(YEAR, c.ContributionDate) as Year
INTO #contribs
FROM Contribution c 
WHERE ((c.ContributionDate >= @startDate AND c.ContributionDate <= @Today) OR
    (c.ContributionDate >= @startDatePY AND c.ContributionDate <= @TodayPY)) AND
    c.ContributionTypeId <> 6 -- exclude returned checks
    AND c.ContributionStatusId <> 2 -- exclude unapproved(?)
GROUP BY c.FundId, DATEPART(MONTH, c.ContributionDate), DATEPART(YEAR, c.ContributionDate);

SELECT SUM(c.giving) as Giving,
    fsf.FundSetId, 
    c.month as Month,
    c.year as Year,
    COALESCE(fs.description, cf.FundName) as Fund,
    SUM(CAST(CAST(JSON_VALUE(@BudgetJson, CONCAT('$."', @Year, '"."', cf.FundId, '"')) AS MONEY) AS DECIMAL(18,2))) AS Budget
INTO #grouped
FROM #contribs c
LEFT JOIN ContributionFund cf ON c.FundId = cf.FundId
LEFT JOIN FundSetFunds fsf ON c.FundId = fsf.FundId
LEFT JOIN FundSets fs ON fsf.FundSetId = fs.FundSetId
GROUP BY c.Month, c.year, fsf.FundSetId, COALESCE(fs.description, cf.FundName);

SELECT *
INTO #summed 
FROM (
    SELECT
        SUM(g.Giving) as Giving,
        g.Fund,
        g.Budget,
        g.Year
    FROM #grouped g 
    WHERE (@year <= 2023 AND g.FundSetId IN (2, 5, 6)) 
        OR (@year >= 2024 AND g.FundSetId IN (1)) 
    GROUP BY g.Fund, g.Budget, g.Year

    UNION
    
    SELECT
        SUM(g.Giving) as Giving,
        CONCAT(g.Fund, ' (', @MonthName, ')') As Fund,
        g.Budget,
        g.Year
    FROM #grouped g 
    WHERE g.month = @Month 
        AND (
            (@year <= 2023 AND g.FundSetId IN (4)) 
            OR (@year >= 2024 AND g.FundSetId IN (4)) 
        )
    GROUP BY g.Fund, g.Budget, g.year
) as summed;

SELECT c.Fund,
	c.Giving AS 'Giving YTD',
	c.Budget AS 'Budget FY',
	c.Budget * @PctOfYear AS 'Budget YTD',
	c.Giving - c.Budget * @PctOfYear AS 'YTD Difference',
	(c.Giving - c.Budget * @PctOfYear) * 100 / (c.Budget * @PctOfYear) AS 'YTD Pct',
	c.Giving - c.Budget AS 'FY Difference',
	(c.Giving - c.Budget) * 100 / c.Budget  AS 'FY Pct',
	p.Giving AS 'Giving PYTD',
	c.Giving - p.Giving AS 'PY Difference',
	(c.Giving - p.Giving) * 100 / p.Giving  AS 'PY Pct',
	CAST(@Today AS DATE) AS 'As Of',
	@year as 'Year'
FROM #summed c
    LEFT JOIN #summed p ON c.Fund = p.Fund AND c.Year = p.Year + 1
WHERE c.Budget > 0 AND c.year = @year
UNION 
SELECT c.Fund,
	c.Giving AS 'Giving YTD',
	null AS 'Budget FY',
	null AS 'Budget YTD',
	null AS 'YTD Difference',
	null AS 'YTD Pct',
	null AS 'FY Difference',
	null AS 'FY Pct',
	p.Giving AS 'Giving PYTD',
	c.Giving - p.Giving AS 'PY Difference',
	(c.Giving - p.Giving) * 100 / p.Giving  AS 'PY Pct',
	CAST(@Today AS DATE) AS 'As Of',
	@year as 'Year'
FROM #summed c
    LEFT JOIN #summed p ON c.Fund = p.Fund AND c.Year = p.Year + 1
WHERE c.Budget IS NULL AND c.year = @year
ORDER BY c.Giving DESC
