qd = None

model.Title = "Enagement Report"
shepherdEV = "Shepherd PID"

if model.Data.p == "":  # Blue Toolbar Page load
    qd = q.BlueToolbarReport()
else:
    qd = q.QueryList("PeopleIds = '{}'".format(Data.p))
    
    print """<p>You're probably here because you were assigned a task to reach out to someone on the \"not seen lately\" list.  You may have even been assigned someone that you <i>have</i> seen lately.  If that's the case, any one of the following could have prevented this task:
<ul>
<li>Fill out the communion attendance slips</li>
<li>Record one-on-one meetings and calls</li>
<li>Consistently submit attendance from Small Group and Bible School classes</li>
</ul></p>

"""
print "<div style=\"display:flex; flex-wrap: wrap;\">"

enagementSql = model.SqlContent("Engagement")

for p in qd:
    print "<div class=\"well\">"
    
    print "<h2><a href=\"/person2/{}\">{}</a></h2>".format(p.PeopleId, p.Name)
    
    shep = p.Family.GetExtraValue(shepherdEV)
    if shep is not None:
        shep = shep.IntValue
    if shep is not None:
        for s in q.QueryList(shep):
            shep = s
            break
        print "<p><b>Assigned Shepherd: <a href=\"/person2/{}\">{}</a></b></p>".format(shep.PeopleId, shep.Name)
    else:
        print "<p><b>Assigned Shepherd: none</b></p>"
        
    print "<h3>Latest Interactions</h3>"
    
    print "<table class=\"table\"><tr><th>Date</th><th>Type</th><th>Detail</th><th>Leader</th></tr>"
    for e in q.QuerySql(enagementSql, p.PeopleId, None):
        print "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(e.Date, e.Action, e.Detail, e.Leader)
    print "</table>"
    
    print "<p>Coming soon... small groups closest to {}'s home</p>".format(p.NickName or p.FirstName)
    
    print "</div>"
    
else:
    print "<p>No people provided</p>"
    
print "</div>"