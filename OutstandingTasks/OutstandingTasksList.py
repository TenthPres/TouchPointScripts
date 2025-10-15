# from pprint import pprint

global model, Data, q

if Data.Person:
    peopleId = Data.Person.PeopleId
elif Data.pid:
    peopleId = Data.pid
else:
    peopleId = model.UserPeopleId

taskSql = """
SELECT *, COALESCE(abt.NickName, abt.FirstName) AS GoesBy FROM TaskNote tn JOIN People abt ON tn.AboutPersonId = abt.PeopleId
WHERE (
    (tn.OwnerId = {0} AND tn.AssigneeId IS NULL) OR 
    (tn.AssigneeId = {0})
) AND tn.StatusID <> 1 AND tn.StatusId <> 5 AND tn.StatusId <> 6
""".format(peopleId)

for task in q.QuerySql(taskSql, peopleId, None):
    instr = model.Markdown(task.Instructions)

    print("""<div style=\"Border: 2px solid black; margin:2em 2em 0; padding:2em;\">
    <table>
    <tr><td>About</td><td>{0}</td></tr>
    <tr><td>Email</td><td>{1}</td></tr>
    <tr><td>Phone</td><td>{2}</td></tr>
    <tr><td>Created</td><td>{5}</td></tr>
    <tr><td colspan="2"><a href=\"{3}/Person2/{4}#tab-touchpoints\">Full Profile</a> (may require permissions you don't have)</td></tr>
    </table>
    
    <div style=\"padding:2em;\">
        <a href=\"{3}/Person2/0?v=Action#tab-touchpoints\">{6}</a>
    </div>
    
    <p>Please respond as needed and mark the task Complete</p>
    
    </div>""".format(task.GoesBy + " " + task.LastName, task.EmailAddress, model.FmtPhone(task.CellPhone), model.CmsHost, task.PeopleId, task.CreatedDate, instr))