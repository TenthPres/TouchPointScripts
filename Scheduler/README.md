# Scheduler

There are a few simple scripts to make it easier to work with the Volunteer Scheduler. 

## CommitmentListingForFuture

This script simply lists all upcoming commitments for an involvement for a certain number of days in the future. 
You'll need to change the Involvement ID and number of days to look forward at the top. 

## SchedulerSyncing

This python script is intended to run daily (and manually for configuration) to sync scheduler involvements with the 
other non-scheduler involvements they serve.  It can do this in a few different ways:
- Assume Present -- For our tech volunteers, if they're signed up, we generally assume they're going to show up.  
  Therefore, they are marked present by default. The team leader can always take attendance in the usual way to mark 
  these individuals absent, or mark others present. 
- Apply Attendance Elsewhere -- Our ushers and tech volunteers are, by doing their job, attending the worship service.
  Therefore, if they are marked present (or scheduled) in the scheduler, they are marked present in the worship service 
  attendance.
- Assign to Other Involvements -- For our nursery, we have one central scheduler for all of our 
  Nursery volunteers, but we have different involvements and roles for each age group.  This script will take the 
  volunteers signed up in the scheduler and put them in the appropriate involvement and leadership role based on the 
  team and subgroup they are signed up for. 

## CommitmentStatusFlag

Let's say you need your elders to sign up to serve communion 20 times per year.  It would be helpful to know which elders
have done that, so you can email those who haven't. Copy this script to Special Content, then create a status flag with
the criteria, "In SQL List" with the appropriate script name. You'll need to modify the script for the Involvement ID, 
date range (days past and days future), and the target count (@Cnt)