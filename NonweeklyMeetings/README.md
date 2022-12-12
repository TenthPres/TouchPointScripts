# Non-Weekly Meetings

This script creates meetings (and therefore causes attendance reminders to be sent) for Involvments that don't meet weekly.  To use this, install the script, and add it to your Morning Batch. 

You'll also need to add a Standard Extra Value for Involvements of the Bits/Checkboxes type with the following values:

```
Frequency:Every Other
Frequency:First
Frequency:Second
Frequency:Third
Frequency:Fourth
Frequency:Fifth
```

Then, when the batch runs, it'll create the meetings if they don't already exist. 