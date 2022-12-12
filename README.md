# TouchPointScripts
This is a collection of scripts, widgets, and other handy bits for use with TouchPoint Software, the Church Management 
System we call "MyTenth." 

## Tools Available Now

- [**Attendance Redirect**](AttendanceRedirect) - This tool helps get people to the right Registration for Record Family Attendance.

- [**Assign Shepherd**](AssignShepherd) - This tool allows leaders to be assigned as designated "shepherds" for a family.  
This shepherd can then be referenced in Tasks or when Counseling situations arise. 

- [**Children's Involvement Rules**](Children's Involvement Rules) - When added to your daily batch, this script will make sure any
Children's Involvements have their proper Extra Values applied, such as the MinistrySafe and Background check heart and checkmark 
icons on volunteer nametags. 

- [**Email Address Archiving**](EmailAddressArchiving) - TouchPoint can only store two email addresses per user.  While most
people probably only use one or two email addresses at a time, it can be helpful to keep track of all of the email addresses
someone uses across time.  This script allows many more email addresses to be immutably associated with a person's record,
making future data imports significantly less likely to produce duplicates.  This script is strongly encouraged for the 
Mailchimp and ConstantContact integrations. 

- [**Engagement Widget**](EngagementWidget) - Compare your populations of attenders, members, and givers. See how (or if) they
overlap.
  
- [**Finance > Budget Summary**](Finance%20Reports) - List each budgeted fund and where giving stands compared to budget.
  
- [**Global > Birthdays & Anniversaries**](Global%20Reports) - Generate a list of partners who have birthdays or 
anniversaries coming up, and email it to the appropriate people.  We use this to send cards to partners each month.

- [**Mailchimp Sync**](Mailchimp) - Sync Mailchimp subscribers both ways (from Mailchimp to TouchPoint and vice versa), 
across multiple Mailchimp accounts and with Mailchimp Interests as TouchPoint Subgroups.

- [**Non-Weekly Meetings**](NonweeklyMeetings) - This script, when added to your Morning Batch, automatically creates meetings for 
non-weekly Involvements based on Extra Values on the Involvement. Once the meetings are created, automatic attendance reminders will
be sent. 

- [**Recent Attendance Trends**](RecentAttendanceTrends) - This is a minor update from the standard Recent Attendance Trends widget
that ships with TouchPoint, which will use a sliding window of 90 days, rather than a date you need to set. 
  
- [**Recent Communion**](RecentCommunion) - Indicate who has attended services where communion has been served.

- [**Registrations in Progress**](RegistrationsInProgress) - Show the most recent 100 registrations that have been started but 
not completed.  Can be very helpful in diagnosing issues users encounter with registrations. 

- [**Role Checker**](RoleChecker) - Automatically update the roles users have as part of the Morning Batch process.  While
this doesn't remotely handle all the roles, it does handle those that are most important for us and most likely to change.

- [**Sage Intacct**](SageIntacct) - Create a reconciliation report that readily imports into Sage Intacct, as required by
AcctTwo, our accounting firm. 

- [**Scheduler**](Scheduler) - A few scripts to fill gaps in getting data out of the Volunteer Scheduler. 

- [**Vital Stats Widget** *With Bars!*](VitalStatsWidget) - Add a subtle bar chart to your Vital Stats widget. 

## Tools Under Development


- [**AD Sync**](ADSync) - Automatically sync your church directory into your staff's email & contact directory.

- [**Mapify**](Mapify) - Wondering which neighborhoods need a new Small Group?  Or where your attendees actually come from?  See 
people from any search (or Involvement or any other scenario with a Blue Toolbar) on a highly-interactive globe of the world.

- [**PA Background Check Automation**](BackgroundChecks) - Pennsylvania has weird and specific laws about how background 
checks are conducted.  This tool tracks their progress, their renewals, and (so far as we are able within the law) automates 
the process for both staff members and volunteers. 

- [**ConstantContact Sync**](ConstantContact) - Sync ConstantContact subscribers both ways (from ConstantContact to 
TouchPoint and vice versa). 
  
- [**Tuition Automation**](TuitionAutomation) - Automatically calculate and bill tuition for ongoing programs (e.g. 
  preschool).

## Tools No Longer Necessary
Occasionally, the TouchPoint team redevelops tools we've created in Python as genuine features in the main TouchPoint system.  When that happens,
our OG tool becomes unnecessary.  But, for posterity, here are those tools:

- [**ChangeLog**](ChangeLog) - This report lists the most recent changes made to a Person or Family.  It shows the person 
making the change, the person to whom the change was made, and the content of the changes.

- [**Summon Parent**](SummonParent) - This is a tool intended for children's workers to "summon" parents when needed.  We have it 
linked within the Mobile App, so workers can send a text in just a few taps, without revealing the personal phone number of either 
the parent or the volunteer.  Eventually, we hope to integrate this with our pager system, as well. 