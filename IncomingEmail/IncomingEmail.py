#API

# Identify user, if possible.  (Person with the most attendance, with the matching email address)
findPersonByEmailSql = """
SELECT TOP 100 PeopleId
FROM People p WHERE LOWER(EmailAddress) = LOWER('{0}') OR LOWER(EmailAddress2) = LOWER('{0}')
ORDER BY (SELECT COUNT(*) FROM Attend a WHERE a.PeopleId = p.PeopleId AND a.AttendanceFlag = 1 AND a.MeetingDate > DATEADD(month, -6, GETDATE())) DESC
"""

Data.FromPid = q.QuerySqlInt(findPersonByEmailSql.format(Data.From))

unknownUserPid = 29120

Data.To = Data.To.lower().split(';')
Data.Subject = Data.Subject.strip() if Data.Subject is not None else ""
Data.Body = Data.Body.strip() if Data.Body is not None else ""

if Data.Subject[0:3].lower() == "fwd" or Data.Subject[0:3].lower() == "fw:":
    pass

elif "asprayer@tenth.org" in Data.To:
    noteBody = ""
    if Data.Subject != "":
        noteBody = "**" + Data.Subject + ":**  "
    
    noteBody += Data.Body
    
    if Data.FromPid == 0:
        noteBody += """
        
        Submitted by {}""".format(Data.From)
        
        Data.FromPid = unknownUserPid
        
        model.CreateTaskNote(Data.FromPid, Data.FromPid, None, None, True, None, noteBody, None, [7, 59])
        print "Your prayer request has been submitted.  Thank you.  We don't have your email address on file.  Please reply with your name."
        
    else:
        model.CreateTaskNote(Data.FromPid, Data.FromPid, None, None, True, None, noteBody, None, [7, 59])
        print "Your prayer request has been submitted.  Thank you."
        
elif "care@tenth.org" in Data.To:
    noteBody = ""
    if Data.Subject != "":
        noteBody = "**" + Data.Subject + ":**  "
    
    noteBody += Data.Body
    
    owner = 29218
    
    if Data.FromPid == 0:
        noteBody += """
        
        Submitted by {}""".format(Data.From)
        
        Data.FromPid = unknownUserPid
        
        model.CreateTaskNote(owner, Data.FromPid, None, 55, False, noteBody, None, None, [29], True)
        print "Thank you.  We'll be in touch shortly.  We don't have your email address on file.  Please reply with your name."
        
    else:
        model.CreateTaskNote(owner, Data.FromPid, None, 55, False, noteBody, None, None, [29], True)
        print "Thank you.  We'll be in touch shortly."


# Unknown cases
elif "automation@tenth.org" in Data.To:
    
    noteBody = "**Unrecognized Incoming Message**  {} : {}".format(Data.Subject, Data.Body)
    
    if Data.FromPid == 0:
        Data.FromPid = unknownUserPid
    
    model.CreateTaskNote(12255, Data.FromPid, None, None, False, noteBody, None, None, [])
    
else:
    print "Sorry, I'm just an automation and I'm not sure what to do with this message.  Please email dbhelp@tenth.org to get it streightened out."

# pprint(Data)
