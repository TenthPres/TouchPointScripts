sql = """SELECT p.PeopleId, tn.CreatedDate Submitted, COALESCE(p.NickName, p.FirstName) First, p.LastName Last, tn.Notes [Request] FROM TaskNoteKeyword tnk 
    JOIN TaskNote tn ON tnk.TaskNoteId = tn.TaskNoteId 
    LEFT JOIN People p ON tn.AboutPersonId = p.PeopleId
    WHERE tnk.KeywordId = 59
        AND tn.CreatedDate > DATEADD(week, -1, DATEADD(hour, -1, GETDATE()))
    ORDER BY tn.CreatedDate DESC"""
    
results = q.QuerySql(sql)

print "<table><tr><th>Submitter</th><th>Request</th></tr>"

for r in results:
    print "<tr><td><a href=\"https://my.tenth.org/Person2/{}\">{}&nbsp;{}</a></td><td>{}</td></tr>".format(r.PeopleId, r.First, r.Last, model.Markdown(r.Request))
    
print "</table>"

print """<script>setTimeout("location.reload(true);",15000);</script>


<style>

td, th {
   padding: .5em;
}

</style>

"""