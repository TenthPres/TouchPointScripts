# Engagement Widget

Shows a proportional venn diagram of the three major categories of engagement: Attendance, Membership, and Giving.  This lets you see how these groups
overlap.

![Engagement Widget Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/EngagementScreenshot.gif?raw=true)

## Installation
1.  In Special Content, create a new Text file with the full contents of [EngagementWidgetHTML.html](EngagementWidgetHTML.html).  Be sure to give it 
the `Widget` keyword.  (Confusingly, TouchPoint classifies these HTML snippets as Text files, rather than HTML files.)

1.  In Special Content, create a new Python file with the full contents of [EngagementWidgetPython.py](EngagementWidgetPython.py).  Be sure to give it
the `Widget` Keyword.

1.  Customize your Python script.  The defaults (Attenders, Givers and Members) will work for anyone with a Finance Role.  The searches are defined 
starting on line 7 of the Python script.  For each search, there are four parameters:
    - **Title** - This is the label that is shown initially, and are used as the headers for the categories.  Avoid using special characters here.

    - **Description** - Describe the criteria, as if you're finishing a sentence that starts with "People who...".  For intersections (where circles
    overlap), these phrases are automatically strung together.

    - **Search Code** - The search criteria.  You can make any search in the Query Builder and then get the code from the bottom of the criteria window.

    - **Color** *(optional)* - If you want the region to show in a specific color, you can set it here as a 
    [hex triplet](https://en.wikipedia.org/wiki/Web_colors#Hex_triplet).  Or, you can remove this line, and use the default colors.

    - If you want "Givers" to be visible to non-finance users, without amounts, 
    [create a status flag for it](https://docs.touchpointsoftware.com/People/StatusFlags.html#saved-searches) and change the Search Code to use the 
    status flag instead. 

    - You technically can add additional searches by adding more search criteria.  However, it may not work very well if they don't significantly 
    intersect with your existing searches.  Increasing searches increases the number of constraints the charting library needs to figure out, and that 
    decreases the likelihood that everything will plot correctly. 

1.  Add the Widget to the Homepage Widgets.  From the Admin > Homepage Widgets page, Add New.  Set the Name, Description and Roles as you wish.  Select 
the View and Python files that we created earlier.  There is no SQL file for this widget. For caching, we recommend using **each day** for **each user**.  
The 'each user' part is important if OrgLeaderOnly users are able to see it, because their search results will be different from those with broader access.


## Licensing & Charting
**Summary:Charting library requires attribution and a free license.  Widget requires remaining open source.  If you don't substantially modify the
code, the defaults will work for you.**

Like the other scripts in this repository, this widget is licensed under [AGPL](https://en.wikipedia.org/wiki/Affero_General_Public_License).  

TouchPoint's default charting library ([Google Charts](https://developers.google.com/chart/)) does not have a Venn feature, so this widget uses 
[Highcharts](https://www.highcharts.com/) instead.  

**[You need a license to use Highcharts, which is free for nonprofits.](https://shop.highsoft.com/highsoft/form/noncommercialform)**  That license 
allows use under [Creative Commons Attribution-NonCommercial](https://creativecommons.org/licenses/by-nc/3.0/), which means you must credit Highcharts
for the charting library somewhere reasonable.  By default, this is at the bottom right of the widget. 