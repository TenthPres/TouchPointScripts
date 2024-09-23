# Financial Reports

This is a collection of simple reports used to report on giving.  

- [**Budget Summary (SQL)**](BudgetSummary.sql) - List each budgeted fund and where giving stands compared to budget. 
    
  ![Budget Summary Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/BudgetSummary.png?raw=true)
    
  For this report, it is assumed that you put the budgeted amounts, by year, in a separate text file called [Budgets.json](Budgets.json). 

- [**Budget Summary (Python)**](BudgetSummary.py) - A Python script that takes the Budget Summary SQL above and makes it a bit more readable.

  ![Budget Summary Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/BudgetSummaryPy.png?raw=true)

- [**Budget Summary Chart**](BudgetSummaryChart.py) - A Python script that takes the Budget Summary SQL above and renders it into a chart in SVG format.

<div style="background:#fff">

  ![Budget Summary Chart Screenshot](https://www.tenth.org/touchpoint-api/report/py/BudgetSummaryChart/svg)

</div>

- [**Cumulative Giving YoY (SQL)**](BudgetCumulativeGivingYoY.sql) - Compare giving year-over-year as a percentage of budget, week by week.

- [**Cumulative Giving Comparison to Budget**](BudgetCumulativeComparison.py) - A Python script that takes the Cumulative Giving YoY SQL above and 
  renders it into a chart that allows for comparison to previous years. 

  ![Cumulative Giving Comparison to Budget Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/CumulativeGivingYoY.png?raw=true)