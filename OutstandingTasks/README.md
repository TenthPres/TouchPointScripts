# Outstanding Tasks

This module has several related components.  The first, [OutstandingTasksList.py](OutstandingTasksList.py) is a Python 
script that generates a list of outstanding tasks for the current user with some links and instructions.  
This can be used in email templates, or as a report. 

Then, there are several files that work together to send reminder emails to users with outstanding tasks. 

The first of these files is [TaskNote-ToDo.sql](TaskNote-ToDo.sql), which generates a list of the people who have
outstanding Tasks, but excludes New People entry tasks.  This is used as the recipient list for the email.

Next, you'll need an email template with a particular replacement code.  The content of our email is in 
[OutstandingTasksReminderEmail.md](OutstandingTasksReminderEmail.md).  It is imperative that you include the replacement
tag `{pythonscript:OutstandingTasksList}`, which inserts the output of the report above. Our template is called 
'OutstandingTasksReminder'.  You can either use that name, or change the name in the Python script below.

The final file is [OutstandingTaskNotifications.py](OutstandingTaskNotifications.py), which is a Python script that 
actually sends the email to the people in the recipient list above.

To have messages go out automatically, you can *either*: 
1.  Add this line to your MorningBatch python script: 
    ```python
    if model.DayOfWeek == 2: # Tuesday mornings
        model.CallScript('OutstandingTaskNotifications')
    ```
    
2.  Or, you can add something like this to your ScheduledTasks python script, which gives you a little more control 
over when the email is sent:
    ```python 
    if model.ScheduledTime == "1900" and model.DayOfWeek == 2: # T @ 7pm
        print(model.CallScript('OutstandingTaskNotifications'))
    ```
    As written here, this will send on Tuesdays at 7pm (which is what we do).