global model

mainQuery = model.SqlContent('BackgroundChecks-Status')

model.Title = "Background Check Notifications"

sql = """
{0};

SELECT * FROM #status
WHERE DaysToAction = 0 OR DaysToAction = 60 OR DaysToAction = 30;

""".format(mainQuery.replace("-- INTO", "INTO"))


d60 = []
d30 = []
d0 = []

for row in model.SqlListDynamicData(sql):
    if row.DaysToAction == 0:
        d0.append(row.PeopleId)

    elif row.DaysToAction == 30:
        d30.append(row.PeopleId)

    elif row.DaysToAction == 60:
        d60.append(row.PeopleId)


d60 = map(str, d60)
d30 = map(str, d30)
d0 = map(str, d0)

if len(d60) > 0:
    model.EmailContentWithSubject("PeopleIds = '{}'".format(','.join(d60)), 22029, "kbryant@tenth.org", "Karen Bryant", "Your Background Checks are Expiring Soon", "BackgroundCheck-60")

if len(d30) > 0:
    model.EmailContentWithSubject("PeopleIds = '{}'".format(','.join(d30)), 22029, "kbryant@tenth.org", "Karen Bryant", "Your Background Checks are Expiring Soon", "BackgroundCheck-30")

if len(d0) > 0:
    model.EmailContentWithSubject("PeopleIds = '{}'".format(','.join(d0)), 22029, "tgeiger@tenth.org", "Tim Geiger", "Your Background Checks are Invalid", "BackgroundCheck-0")


sql = """
{0};

SELECT *, IIF(DaysToAction < -9, 'Delinquent', IIF(DaysToAction < 2, 'Expired', 'Soon')) as st
FROM #status s
WHERE DaysToAction < 31
ORDER BY St, LastName;

""".format(mainQuery.replace("-- INTO", "INTO"))

from pprint import pprint

Data.lDeli = []
Data.lExpi = []
Data.lSoon = []

for row in model.SqlListDynamicData(sql):
    if row.st == "Delinquent":
        Data.lDeli.append(row)
    elif row.st == "Expi":
        Data.lExpi.append(row)
    elif row.st == "Soon":
        Data.lSoon.append(row)

from datetime import datetime

if datetime.now().weekday() == 5:

    t = '''
        <p>This is your weekly automated Background Check status update.</p>
    
        <p>The following people have some component of their background checks expiring in 30 days or less:</p>
        <ul>
        {{#each lSoon}}
            <li>{{GoesBy}} {{LastName}} (expires in {{DaysToAction}} days, {{ActionRequired}})</li>
        {{else}}
            <p>(none)</p>
        {{/each}}
        </ul>
        
        <p>The following people have had a component of their background checks expire within the last week(ish) <b>and have been notified that they may no longer serve</b>:</p>
        <ul>
        {{#each lExpi}}
            <li>{{GoesBy}} {{LastName}} (expired {{ActionRequired}})</li>
        {{else}}
            <p>(none)</p>
        {{/each}}
        </ul>
        
        <p>The following people have invalid, incomplete, or longer-expired background checks:</p>
        <ul>
        {{#each lDeli}}
            <li>{{GoesBy}} {{LastName}}</li>
        {{else}}
            <p>(none)</p>
        {{/each}}
        </ul>
    '''

    em = model.RenderTemplate(t)

    model.Email("UserRole IN ( 30[BackgroundCheck], 83[BackgroundCheckRun], 87[BackgroundCheckLight] )", 22029, "dbhelp@tenth.org", "Tenth Church Administration", "Background Check Update", em)