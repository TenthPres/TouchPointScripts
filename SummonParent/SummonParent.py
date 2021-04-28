from pprint import pprint

model.Title = "Summon Parent"

# TODO filter to events where it makes sense to reach out to parents. 

meetingQ = '''
    SELECT TOP 1 a.MeetingId, m.*, o.OrganizationName 
    FROM Attend a 
        JOIN Meetings m ON a.MeetingId = m.MeetingId 
        JOIN Organizations o ON m.OrganizationId = o.OrganizationId
        WHERE PeopleId = {} AND 
            a.AttendanceFlag = 1 AND 
            ABS(DATEDIFF(mi, getDate()-1, m.MeetingDate)) < 14400 -- should be 1440 for 24 hours
        ORDER BY ABS(DATEDIFF(mi, getDate()-1, m.MeetingDate)) ASC
'''.format(model.UserPeopleId)

orgMeeting = q.QuerySqlTop1(meetingQ)

if orgMeeting is None:
    print "<p>You are not currently present in a meeting with parent summoning enabled.</p>"
    
else:

    print "<h2>{}</h2>".format(orgMeeting.OrganizationName)
    
    print "<p>{}  (Meeting ID: {})</p>".format(orgMeeting.MeetingDate, orgMeeting.MeetingId)
    
    attenderQ = '''
        SELECT TOP 100 
            pc.PeopleId as childPid,
            COALESCE(pc.NickName, pc.FirstName) as childGoesBy, 
            pc.LastName as childLast, 
            a.Pager as pager,
            
            ph.PeopleId as p1Pid,
            COALESCE(ph.NickName, ph.FirstName) as p1GoesBy,
            ph.LastName as p1Last,
            ph.CellPhone as p1Cell,
            
            ps.PeopleId as p2Pid,
            COALESCE(ps.NickName, ps.FirstName) as p2GoesBy,
            ps.LastName as p2Last,
            ps.CellPhone as p2Cell
            
        FROM Attend a 
            JOIN People pc ON a.PeopleId = pc.PeopleId
            JOIN Families f ON pc.FamilyId = f.FamilyId
            LEFT JOIN People ph ON f.HeadOfHouseholdId = ph.PeopleId
            LEFT JOIN People ps on f.HeadOfHouseholdSpouseId = ps.PeopleId
            
        WHERE MeetingId = {} AND
            a.AttendanceFlag = 1
            
        ORDER BY COALESCE(pc.NickName, pc.FirstName)
    '''.format(orgMeeting.MeetingId)
    
    
    if model.HttpMethod == 'post' and model.Data.a == "send":  # Posting a message to be sent
    
        print " "
        # TODO verify that person should be allowed to send such a thing, to the given recipient. 
    
        sendGroup = q.QuerySqlInt("SELECT TOP 1 ID from SmsGroups")  # TODO eventually: make this vaguely intelligent or something
    
        # TODO change for model.Data.to
        print model.SendSms('PeopleId = {}'.format(model.UserPeopleId), sendGroup, "Parent Summoning", model.Data.message)
    
    else:
    
        for a in q.QuerySql(attenderQ):
            
            print '<div class="attendee">'
            
            print "<h3>{} {}</h3>".format(a.childGoesBy, a.childLast)
            
            if a.p1Cell != None and a.p1Cell != '':
                print '''<a href="#" onclick="prepText({0}, '{1}', this);" class="btn btn-primary">Text {2} {3}</a>'''.format(a.p1Pid, a.childGoesBy, a.p1GoesBy, a.p1Last)
                
            if a.p2Cell != None and a.p2Cell != '':
                print '''<a href="#" onclick="prepText({0}, '{1}', this);" class="btn btn-primary">Text {2} {3}</a>'''.format(a.p2Pid, a.childGoesBy, a.p2GoesBy, a.p2Last)
            
            print '''<a href="#" onclick="page({0});" class="btn btn-outline btn-default disabled">Page</a>'''.format(a.childPid)
            
            print "</div>"
            
        print """
        
        <script defer src="//cdn.jsdelivr.net/npm/sweetalert2@10"></script>
        <script>
        let prepText = function(to, about, caller) {
        
            function getPyScriptAddress() {
                let path = window.location.pathname;
                return path.replace("/PyScript/", "/PyScriptForm/");
            }
        
            Swal.fire({
                title: caller.innerText,
                input: 'textarea',
                inputAttributes: {
                    autocapitalize: 'off'
                },
                footer: "Message will be sent from the church's number.  You will not receive replies.",
                inputValue: "We need help with " + about + ".  Please come.  \\n\\n[This is a one-way message; we won't get replies.]",
                showCancelButton: true,
                confirmButtonText: 'Send',
                showLoaderOnConfirm: true,
                preConfirm: (message) => {
                    postData = {
                        to: to,
                        message: message
                    }
                    let formBody = [];
                    for (const property in postData) {
                        formBody.push(encodeURIComponent(property) + "=" + encodeURIComponent(postData[property]));
                    }
                    
                    return fetch(getPyScriptAddress() + "?a=send", {
                        method: 'POST',
                        body: formBody.join("&"),
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
                        }
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(response.statusText)
                        }
                        return response.blob()
                    })
                    .catch(error => {
                        Swal.showValidationMessage(
                            `Request failed: ${error}`
                        )
                    })
                },
                allowOutsideClick: () => !Swal.isLoading()
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        title: 'Sent!'
                    })
                }
            })
        }
        
        
        
        </script>
        
        <style>
        .attendee {
            margin: 0 0 1em;
            border: 1px solid #999;
            padding: 1em;
        }
        
        div.attendee h3 {
            margin-top: 0;
        }
        </style>
        
        
        
        
        """
