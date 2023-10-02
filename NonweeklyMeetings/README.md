# Non-Weekly Meetings

This script creates meetings (and therefore causes attendance reminders to be sent) for Involvements that don't meet weekly.  To use this, install the script, and add it to your Morning Batch.

## Installation
1.  Download the NonweeklyMeetings zip file from [the releases](https://github.com/TenthPres/TouchPointScripts/releases) 
    and upload the whole zip file to `mychurch.tpsdb.com/InstallPyScriptProject`.  This
    will install the script, and add the meeting creation script to the morning batch. 

## Usage
After installation, you will find a set of Standard Extra Values in your Involvements for "Meeting Frequency".  Check
these boxes as appropriate.  **You must also check "Does NOT Meet Weekly" for these involvements.**

"Every Other" is based on the previous meeting.  So, it will automatically create a new meeting two weeks after the 
previous meeting that wasn't marked "Did not meet".

Then, when the batch runs (or you manually run the NonweeklyMeetings script), it'll create the meetings if they don't 
already exist. 

Involvements with multiple schedules aren't supported.  Your milage may vary. 