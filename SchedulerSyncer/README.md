## SchedulerSyncing

This python script is intended to run daily to sync scheduler involvements with the
other non-scheduler involvements they serve.  It can do this in a few different ways:
- Assume Present -- For our tech volunteers, if they're signed up, we generally assume they're going to show up.  
  Therefore, they are marked present by default. The team leader can always take attendance in the usual way to mark
  these individuals absent, or mark others present.
- Apply Attendance Elsewhere -- Our ushers and tech volunteers are, by doing their job, attending the worship service.
  Therefore, if they are marked present (or scheduled) in the scheduler, they are marked present in the worship service
  attendance.
- Assign to Elsewhere -- For our nursery, we have one central scheduler for all of our
  Nursery volunteers, but we have different involvements and roles for each age group.  This script will take the
  volunteers signed up in the scheduler and put them in the appropriate involvement and leadership role based on the
  team and subgroup they are signed up for. 

This will ONLY sync recurring, scheduled items, not one-off instances. 

## Installation
1.  Download the SchedulerSyncer zip file from [the releases](https://github.com/TenthPres/TouchPointScripts/releases)
    and upload the whole zip file to `mychurch.tpsdb.com/InstallPyScriptProject`.  This
    will install the script, and add the processing script to the morning batch. 
2.  Once installed, go to `mychurch.tpsdb.com/PyScript/SchedulerSyncer` to start the configuration.  You will see each
    of your scheduler involvements listed, and can configure the settings as you'd like them.  They will be saved and
    applied automatically overnight. 