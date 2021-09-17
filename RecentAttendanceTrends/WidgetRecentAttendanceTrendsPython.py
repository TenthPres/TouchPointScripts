# Users can add divisions to include in the line chart for this widget inside this divisions array.
# This array is made up of objects. Each object contains a name and a division id number.
# The first item in the object is the name you wish to display in the widget for the selected division.
# The second item in the object is the division id you wish to display in the widget.


programs = [
    ['Worship', 7],
    ['Discipleship', 10],
    ['Mercy', 9],
    ['Outreach', 8]
]

# You can change Interval to change the horizontal axis of your chart.
Interval = '14'

import datetime
import json

begindate = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

def GetData(programs, begindate):
    sql = model.Content('WidgetRecentAttendanceTrendsSQL')
    progids = [row[1] for row in programs]
    sql = sql.replace('@begindate', begindate)
    sql = sql.replace('@progs', str(progids)[1:-1])
    rowcountsql = 'isnull((select sum(MaxCount) from data d where d.ProgramId = {0} and d.ss = dd.ss group by d.ss), 0) d{0}'
    rlist = [rowcountsql.format(d) for d in progids]
    s = ',\n'.join(rlist)
    sql = sql.replace('@rowcounts', s)
    rdata = [ [ begindate] + [None for row in programs] ]
    strr = json.dumps(rdata + json.loads(q.QuerySqlJsonArray(sql)))
    strr = strr.replace('/','-').replace('["', '[new Date("').replace('",','T05:00:00Z"),') 
    return strr

def Get():
    sql = Data.SQLContent
    template = Data.HTMLContent
    Data.results = GetData(programs, begindate)
    Data.rowdata = Data.results
    Data.interval = Interval
    addcolumn = "data.addColumn('number', '{}');"
    alist = [addcolumn.format(s[0]) for s in programs]
    Data.addcolumns = '\n'.join(alist)
    # for x in Data.rowdata:
    #   print(Data.rowdata)
    print model.RenderTemplate(template)
    
Get()