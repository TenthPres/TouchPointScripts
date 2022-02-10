# AD Sync

This tool automatically syncs your members' contact info into your church's Active Directory Contacts.  This makes all of your members contact info available to 
staff in your email/contacts client without any special interaction on their part, and without even needing to explicitly use TouchPoint.

To use this, you will need an Active Directory Domain and a willing IT admin.

This should work with:
- On-site Exchange servers,
- Microsoft 365 if you use AAD Connect, 
- Google Workspace if you use the Directory Sync tool, or
- Microsoft 365 if you don't use AAD Connect with some modifications.

As written, this tool will not work with Google Workspace without the Directory Sync tool.

## Components
There are two pieces to this automation, and both are required. 
1.  Python script to run within TouchPoint - This handles the data that gets exported from TouchPoint, and dictates the formatting of the records created in your
directory. 

2.  PowerShell script to be run on a domain controller.  This script should be run daily through the Task Scheduler interface.


