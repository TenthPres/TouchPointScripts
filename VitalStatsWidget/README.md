# Vital Stats Widget *With Bars!*

This is a spin on the Vital Stats widget that ships with TouchPoint that adds a background "bar chart" to each category, to make the data more useful 
for the visually-minded folks. 

![Vital Stats Widget Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/vitalStats.png?raw=true)

## Installation
1.  In Special Content, create or update a Text file with the full contents of [WidgetVitalStatsHTML.txt](WidgetVitalStatsHTML.txt).  Be sure to give it 
the `Widget` keyword.  (Confusingly, TouchPoint classifies these HTML snippets as Text files, rather than HTML files.)

    - If you want a "Total" line, you'll need to remove two lines from near the end of this file.  They're very clearly labeled. 

1.  In Special Content, create or update a Python file with the full contents of [WidgetVitalStatsPython.py](WidgetVitalStatsPython.py).  Be sure to give it
the `Widget` Keyword.

1.  Customize your Python script.  The default status flags are the ones in 
[the TouchPoint documentation](https://docs.touchpointsoftware.com/CustomProgramming/HomepageWidgets/VitalStats.html).  The instructions there apply 
for customizing the searches you use here, as well.  For each search, there are three parameters:
    - **Name** - This is the label shown.

    - **Search** - This is a status flag or saved search that provides the metric you're looking for. 

    - **Link** *(optional)*- If you want the line to be a link to a specific page (e.g. the page where the search can be seen, put the relatively URL here.

    You can add as many searches as you want, just be sure to follow the format.

1.  The widget is probably already on your homepage since this is a stock widget.  But, if it isn't, you should add it to the homepage.  From the 
Admin > Homepage Widgets page, Add New.  Set the Name, Description and Roles as you wish.  Select the View and Python files that we created earlier.  
There is no SQL file for this widget. For caching, we recommend using **each day** for **each user**.  The 'each user' part is important if OrgLeaderOnly u
sers are able to see it, because their search results will be different from those with broader access.

