**This is a work in progress and should currently be used for inspiration only.**

# Tuition Automation

This is a tool intended to automatically bill monthly tuition for students in our Preschool program.  This is a function 
that TouchPoint is *definitely not* built for, so while this solution is  **NOT** an ideal solution, it is a viable 
solutions and provides the level of flexibility we need.

## Limitations
- **Cannot set up automatic recurring payments.**  That's just not a thing that TouchPoint can do. 
- **Requires a separate PayLink for each child.**  So, if multiple children are enrolled, the parent will need to make 
two separate payments each billing cycle.
  
## Features
- **Automatic Discounts** based on attributes in the database.  For example, we have a discount for church members.  If
parents become members during the school year, the discount automatically starts applying when they become members.
- **Manual Override option** for students who may be on scholarship or financial aid.
- **Unified accounts** for each child--any overpayment carries forward to the next term.
- **Automated Billing emails** with the account history and balance.