import re
from pprint import pprint

model.Title  = "Congregational Meeting Ballot"
model.Header = "Congregational Meeting Ballot"

pid = model.UserPeopleId
person = model.GetPerson(pid)

meetingId = 34020

digitalSubgroup = "Digital"
voteSubgroupPrefix = "Vote_"

votingOpen = False
votingComplete = True

issues = {
    "sell": {
        "question": "Motion: The Trustees, along with the unanimous support of the Session, move that the congregation approve the sale of the 315 South 17th Street Building.",
        "options": ["Yes", "No", "Abstain"],
        "limit": 1 # this isn't supported yet, but feels like a good thing to include for later. 
    }
}

def getExistingVotes(voteKey):
    votesPrefix = voteSubgroupPrefix + voteKey + "_"
    query = """
        SELECT t3.Name as Subgroup
            FROM dbo.OrgMemMemTags AS t2
            INNER JOIN dbo.MemberTags AS t3 ON t3.Id = t2.MemberTagId
            INNER JOIN dbo.Meetings AS m ON t2.OrgId = m.OrganizationId
            WHERE m.MeetingId = {}
              AND t2.PeopleId = {}
              AND t3.Name LIKE '{}%';
              """.format(meetingId, pid, votesPrefix)
              
    items = []
    for x in q.QuerySql(query):
        items.append({
            "Subgroup": x.Subgroup,
            "Vote": x.Subgroup[len(votesPrefix):]
        })
    
    return items
    
def getOrgId():
    return q.QuerySqlInt("SELECT TOP 1 m.OrganizationId FROM Meetings m WHERE MeetingId={}".format(meetingId))
    

# Communicant members 18+ (or unknown age)
query = '''
MemberStatusId = 10[Communicant Member]
AND 
(
	Age = ''
	OR Age >= 18
)
AND PeopleId = {}
'''.format(pid)

if Data.checkin == '1':
    orgId = getOrgId()
    
    model.AddSubGroup(pid, orgId, digitalSubgroup)
    model.EditPersonAttendance(meetingId, pid, True)
    print "REDIRECT=/PyScript/Vote"
    
elif votingOpen and Data.vote != '':
    [key, vote] = Data.vote.split("_", 1)
    
    # remove existing votes
    existing = getExistingVotes(key)
    orgId = getOrgId()
    if existing is not None:
        for x in existing:
            model.RemoveSubGroup(pid, orgId, x['Subgroup'])
    
    subgroup = voteSubgroupPrefix + key + "_" + vote
    model.AddSubGroup(pid, orgId, subgroup)
    print "REDIRECT=/PyScript/Vote"


# Check eligibility
elif q.QueryCount(query) < 1:
    print "<p>You are not a Communicant Member of the church and/or are ineligible to vote in this meeting.  If you believe this is a mistake, please talk to an elder.</p>"
    
else:
    query = '''
    SELECT TOP 1 a.MeetingId, a.OrganizationId, (1 * a.AttendanceFlag) as AttendanceFlag, 
      1 * COALESCE((
            SELECT 1
            FROM dbo.OrgMemMemTags AS t2
            INNER JOIN dbo.MemberTags AS t3 ON t3.Id = t2.MemberTagId
            WHERE t3.Name = '{}'
              AND t2.OrgId = a.OrganizationId
              AND t2.PeopleId = a.PeopleId
     ), 0) as Digital
    FROM Attend a WHERE PeopleId = {} AND MeetingId = {};
    '''.format(digitalSubgroup, pid, meetingId)
    
    status = q.QuerySqlTop1(query)
        
    # Check status
    if status is None or status.AttendanceFlag < 1:
        print "<p>You can check in for the meeting digitally here.  <b>If you check in digitally, you MUST vote digitally</b> on this webpage.  If you would rather vote with a paper ballot, DO NOT check in here, but instead go to check-in in Reception Hall.</p>"
        
        print "<p><a href=\"?checkin=1\" class=\"btn btn-default\">Check In</a></p>"

    elif status.Digital < 1:
        print "<p>You are checked in with a paper ballot and therefore may not vote digitally.</p>"
        
    elif not votingOpen and not votingComplete:
        print "<p>You are checked in.  Voting is closed until the question is called.  Keep this tab open and come back to it to vote. You can lock your phone in the meantime.</p>"
        print "<script>setInterval(function() {location.reload();}, 10000);</script>"
        
    elif not votingOpen and votingComplete:
        print "<p>Voting has been closed.</p>"
        
    else:
        ii = 0
        for i in issues:
            ii = ii+1
            
            votes = getExistingVotes(i)
            
            print "<div class=\"well\">"
            print "<h2>Question {}: {}</h2>".format(ii, issues[i]['question'])
            
            if len(votes) > 0:
                print "<p>Your vote has been recorded as shown.</p>"
            
            for o in issues[i]['options']:
                optionKey = result = re.split(r'[^a-zA-Z]', o.lower(), maxsplit=1)[0]
                
                active = False
                for v in votes:
                    if v['Vote'] == optionKey:
                        active = True
                        break
                
                print "<div style=\"margin-bottom:1em;\"><a class=\"btn {}\" style=\"width:100%; max-width:4in;\" href=\"?vote={}_{}\">{}</a></div>".format("btn-primary" if active else "btn-default", i, optionKey, o)
        
            print "</div>"
#
