# Global Outreach Reports

This is a collection of simple reports used to care for our Outreach Partners.  

- [**Birthdays and Anniversaries**](BirthdaysAndAnniversaries.py) - Generate a list of partners who have birthdays or 
  anniversaries coming up, and email it to the appropriate people.  We use this to send cards to partners.

  To install, add BirthdaysAndAnniversaries to your Python Special Content and add something like the following to your
  Morning Batch:
  
  ```
  from datetime import datetime
  from math import ceil
  if datetime.today().weekday() == 1 and int(ceil(datetime.today().day / 7.0)) == 2: # Second Tuesday
    print model.CallScript('BirthdaysAndAnniversaries')
  ```
  
  Ours is configured to send on Second Tuesdays, a week before our Outreach Commission meets.

  You will also need to have a Family Extra Value (Int) with a name "Security Level" and value > 0 on all partner 
  records.  (We use this throughout our reporting and automations.  A higher number means "more secure".)  This report 
  does not take security requirements into account.  Therefore, be careful who has access to this report and who the 
  email is sent to. 