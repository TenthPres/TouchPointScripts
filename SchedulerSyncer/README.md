## SchedulerSyncing

This python script is intended to run periodically to sync scheduler involvements with the
other non-scheduler involvements they serve.  It can do this in a few different ways:
- Assume Present -- For our tech volunteers, if they're signed up, we assume they're going to show up.  Therefore,
  they are marked present in the Tech Scheduler involvement automatically. The team leader can always take attendance
  in the usual way to mark these individuals absent, or mark others present.
- Apply Attendance Elsewhere -- Our ushers and tech volunteers are, by doing their job, attending the worship service.
  Therefore, if they are scheduled in the scheduler, they are marked present in the corresponding worship service
  meeting. 
- Assign Elsewhere -- For our nursery, we have one central scheduler for all of our Nursery volunteers, but we have
  different involvements and roles for each service time and age group.  This script will take the volunteers signed
  up in the scheduler and put them in the appropriate involvement and leadership role based on the team they are signed
  up for. 

This will ONLY sync recurring, scheduled items, not one-off instances. 

## Installation
1.  Download the SchedulerSyncer zip file from [the releases](https://github.com/TenthPres/TouchPointScripts/releases)
    and upload the whole zip file to `mychurch.tpsdb.com/InstallPyScriptProject`.  This
    will install the script, and add the processing script to the morning batch. 
2.  Once installed, go to `mychurch.tpsdb.com/PyScript/SchedulerSyncer` to start the configuration.  You will see each
    of your scheduler involvements listed, and can configure the settings as you'd like them.  They will be saved and
    applied automatically several times per hour.

## Things to Know
 - Only scheduler meetings with recurring schedules are currently supported.  One-off meetings are not supported,
   because mapping them to other involvements get really complicated.
 - Meetings are NOT created in destination involvements.  They need to already exist.
 - Commitments are processed several hours ahead of time, and if using the assign elsewhere option, individuals added
   to destination involvements will be automatically removed several hours after the meeting *start*. 
