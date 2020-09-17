# Export for Intacct

This script exports contributions in a format requested by our accountants (AcctTwo), for importing into Sage Intaact for 
bank deposit reconciliations.  It is among the "Totals By Fund" reports. 

TouchPoint fields are mapped to columns in this report as follows: 
    IncomeFund AS Account,
    IncomeAccount AS IncomeAccount,
    IncomeDept AS Department,
    AccountCode AS Project

We have a "Project of the Month." We decided to use a single fund for this, which allows donors to setup recurring giving to
the "Project of the Month", whatever that month may be. However, since the projects change each month, we needed a different
Project code for Intacct each month. 

To accommodate this, the Project Code for the Project of the month is calculated based on the contribution date as YYYYMM, so
August 2021 would be project 202108.

## How to Install

1. In the Special Content section of TouchPoint, create a new SQL Script called ExportForIntacct.  
1. Paste into that document all of the content from [ExportForIntacct.sql](ExportForIntacct.sql).  
1. Save the file.


## How to Run
1. From the Administration menu, select Totals by Fund.
1. Specify the intended start and end date range.  The other fields of this form are ignored.
1. Under "Other Reports", select "Export For Intacct". 

You will need the Finance view to run this report.  The FinanceViewOnly role is not sufficient because of restrictions imposed
by the TouchPoint data model.
