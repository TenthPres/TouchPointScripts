# Tuition Automation

This is a tool intended to automatically bill monthly tuition for students in our Preschool program.  This is a function
that TouchPoint is *definitely not* built for, so while this solution is  **NOT** an ideal solution, it is a viable
solution and provides the level of flexibility we need.  However, if you want a more capable system, you should probably
look to a true Learning/School/Preschool management system.

## Limitations
- **Cannot set up automatic recurring payments.**  That's just not a thing that TouchPoint can do.
- **Requires a separate PayLink for each child.**  So, if multiple children are enrolled, the parent will need to make
  two separate payments each billing cycle.

## Features
- **Automatic Discounts** based on attributes in the database.  For example, we have a discount for church members.  If
  parents become members during the school year, the discount automatically starts applying when they become members.
- **Manual Override option** for students who may be on scholarship or financial aid.
- **Unified accounts** for each child across related programs, so the main program and aftercare can be billed/payed together.
- **Automated-ish Billing emails** with the account history and balance.

## Setup
1.  Download the TuitionAutomation zip file from the releases and install it at `mychurch.tpsdb.com/InstallPyScriptProject`.
    This will install the scripts, but you will need to customize them.
2.  Create the payment involvement, and also the involvements for each class.  The classes can be child involvements of
    the payment involvement, but this is not required. Take note of the Involvement IDs for all of these involvements.
   3.  Go to Special Content > Python and edit the TuitionAutomation script. Towards the top, you'll see a few variables
       that you'll need to customize: 
       ```python
       paymentOrgId = 51
       minTransactionId = 17000
       ```
       The `paymentOrgId` is the Involvement ID of the payment involvement.
    
       The `minTransactionId` is a means of filtering out older transactions, which is particularly useful if you reuse involvements year to year.
    
       Then, there's a section where each class's parameters are spelled out:
       ```python
       orgs = [
           {
               'id': 209,
               'name': "2-Year-Old",
               'base': 332
           },
           {
               'id': 215,
               'name': "Afternoon - Mon",
               'base': 40,
               'payPer': "meeting",
               'discounts': False
           },
           ...
       ]
       ```
       Each set of {} brackets goes with a single class.  You'll need one of those for each class.  **Important**: 
       billing is processed **in order** along this list, starting at the top.  So, if you want to have a "younger sibling" 
       discount, make sure
       you put these in order with older classes listed first. 
    
       `id` is the Involvement ID of the class. 

       `name` is the name of the Involvement, as you want it to appear on billing statements and transactions. 

       `base` is the amount of tuition to charge.  By default, this is per-month.  

       `payPer` allows for switching to per-meeting billing, rather than per-month.  If you're sticking with the default of per-month, you can remove this field.

       `discounts` can be set false to disallow discounts, such as the sibling discount and church member discount.

## Usage

Once the setup steps are complete, navigate to /PyScript/TuitionAutomation from which you'll be able to access most of 
the features available to you.  

(Much more to be written...)
