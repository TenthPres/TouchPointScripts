# Scheduler

There are a few simple scripts to make it easier to work with the Volunteer Scheduler. 

## CommitmentListingForFuture

This script simply lists all upcoming commitments for an involvement for a certain number of days in the future. 
You'll need to change the Involvement ID and number of days to look foward at the top. 

## CommitmentStatusFlag

Let's say you need your elders to sign up to serve communion 20 times per year.  It would be helpful to know which elders
have done that, so you can email those who haven't. Copy this script to Special Content, then create a status flag with
the criteria, "In SQL List" with the appropriate script name. You'll need to modify the script for the Involvement ID, 
date range (days past and days future), and the target count (@Cnt)