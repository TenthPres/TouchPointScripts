# Export for Intacct

This script exports contributions and registrations in a format requested by our accountants (Baker Tilly), for 
importing into Sage Intacct for bank deposit reconciliations.  It is among the "Totals By Fund" reports. 

TouchPoint fields for Contributions are mapped to columns in this report as follows:
    FundAccountCode AS Project,
    FundIncomeFund AS Fund,
    FundIncomeDept AS Department,
    FundIncomeAccount AS GL

For Registrations, the Involvement must have a text Extra Value called 'SI Coding' and it must match the format:
`pppp-fff-dddd-ggggg` where pppp is a 4-digit Project code, fff is a 3-digit fund code, dddd is a 4-digit department 
code, and ggggg is a 5-digit GL code.

### Project of the Month

We have a "Project of the Month." We decided to use a single TouchPoint fund for this, which allows donors to set up 
recurring giving to the "Project of the Month", whatever that month may be. However, since the projects change each 
month, we needed a different Project code for Intacct each month. 

To accommodate this, the Project Code for the Project of the month is calculated based on the contribution date as 
YYYYMM, so August 2021 would be project 202108.  This can be replaced with some other system by changing the math on 
[line 75](ExportForIntacct.sql#L75). 

If you don't have a project of the month, you can safely set `@ProjectOfMonthFund` to 0 and that feature will not run. 

## How to Install

1. In the Special Content section of TouchPoint, create a new SQL Script called `ExportForIntacct`.  
1. Paste into that document all the content from [ExportForIntacct.sql](ExportForIntacct.sql).  
1. Change the Project of the Month Fund Id to your Project of the Month fund if you have one, or set to 0 if you don't have one. 
1. Save the file.


## How to Run
1. From the Administration menu, select Totals by Fund.
1. Specify the intended start and end date range.  The other fields of this form are ignored and have no impact on the report.
1. Under "Other Reports", select "Export For Intacct". 

You will need the Finance view to run this report.  The FinanceViewOnly role is not sufficient because of restrictions imposed
by the TouchPoint data model.
