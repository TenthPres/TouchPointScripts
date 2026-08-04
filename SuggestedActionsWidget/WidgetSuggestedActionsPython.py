import json
global Data, q, model

def Get():
    # sql = Data.SQLContent
    template = Data.HTMLContent
    # params = { 'pid':  }

    pid = model.UserPeopleId
    if pid == 12255:
        # pid = 2268 # Michel's PID because it's more useful for testing
        # pid = 27989 # Brock
        # pid = 3555  # George 
        # pid = 13158 # Alex Garcia
        # pid = 5179 # Tom Thompson
        # pid = 1
        pass

    Data.results = []
    Data.script = ""

    # Background Checks
    sql = "{0} WHERE PeopleId = {1}".format(model.SqlContent('BackgroundChecks-Status'), pid)
    backgroundCheckStatus = q.QuerySqlTop1(sql)
    if backgroundCheckStatus is None:
        # No background check needed; do nothing
        pass

    elif backgroundCheckStatus.DaysToAction < 1:
        Data.results.append(model.DynamicData({
            "path": "/PyScript/BackgroundCheck",
            "fa": "check",
            "label": "Submit Overdue Background Check",
            "classes": "errant"
        }))
    elif backgroundCheckStatus.DaysToAction < 60:
        Data.results.append(model.DynamicData({
            "path": "/PyScript/BackgroundCheck",
            "fa": "check",
            "label": "Background Checks Expiring Soon",
            "classes": "warn"
        }))


    # For Shepherds: see those assigned to them
    shepCnt = q.QuerySqlInt("SELECT COUNT(*) FROM FamilyExtra WHERE Field = 'Shepherd PID' AND IntValue = {}".format(pid))
    if shepCnt > 0:
        Data.results.append(model.DynamicData({
            "path": "/PyScript/AssignShepherd?ShepId={}".format(pid),
            "fa": "users",
            "label": "My Flock"
        }))


    # Parish Emails
    parishes = json.loads(model.TextContent('Parishes.json'))
    for p in parishes:
        if model.InOrg(pid, p['council']):
            if 'emailList' in p:
                Data.results.append(model.DynamicData({
                    "path": "/Email/{}".format(p['emailList']),
                    "fa": "envelope",
                    "label": "Send {} Parish Email".format(p['name'])
                }))

    CommunionHappeningNowSql = """
                               -- Next Communion
                               SELECT COUNT(*) as cnt
                               FROM MeetingExtra me
                                        JOIN Meetings m ON me.MeetingId = m.MeetingId
                               WHERE me.Field = 'Communion' AND m.MeetingEnd > DATEADD(hour, -2, GETDATE()) AND m.MeetingDate < DATEADD(hour, 2, GETDATE()); \
                               """


    # Communion Attendance
    LastCommunionSql = """
    -- Last Communion for given pid
    SELECT TOP 1
        Date,
        WksAgo
    FROM (
        SELECT 
            tn.DueDate as Date, 
            DATEDIFF(week, tn.DueDate, GETDATE()) as WksAgo
        FROM TaskNoteKeyword tnk 
        JOIN Keyword k ON tnk.KeywordId = k.KeywordId
        JOIN TaskNote tn ON tnk.TaskNoteId = tn.TaskNoteId
        WHERE k.Code = 'CA'
        AND tn.AboutPersonId = {0}
        
        UNION
        
        SELECT 
            a.MeetingDate as Date, 
            DATEDIFF(week, a.MeetingDate, GETDATE()) as WksAgo
        FROM MeetingExtra me 
        JOIN Attend a ON me.MeetingId = a.MeetingId
        WHERE me.Field = 'Communion' 
        AND a.PeopleId = {0} 
        AND a.AttendanceFlag = 1
    ) AS CombinedData
    ORDER BY Date DESC;
    """.format(pid)

    Data.script += """
    function CommunionAction() {
        swal("Please Report Communion", "The next time you attend a service with communion, please report your attendance at tenth.org/communion or by marking the yellow slips.");
        return false;
    }
    """

    LastCommunion = q.QuerySqlTop1(LastCommunionSql)
    CurrentCommunionCount = q.QuerySqlInt(CommunionHappeningNowSql)
    if CurrentCommunionCount > 0:
        Data.results.append(model.DynamicData({
            "path": "https://www.tenth.org/communion",
            "fa": "glass",
            "label": "Report Communion Attendance",
            "classes": "warn"
        }))
    elif LastCommunion is None:
        Data.results.append(model.DynamicData({
            "path": "https://www.tenth.org/communion",
            "fa": "glass",
            "label": "No Recorded Communion",
            "onclick": "return CommunionAction()",
            "classes": "errant"
        }))

    elif LastCommunion.WksAgo > 5:
        Data.results.append(model.DynamicData({
            "path": "https://www.tenth.org/communion",
            "fa": "glass",
            "label": "{} weeks since Communion".format(LastCommunion.WksAgo),
            "onclick": "return CommunionAction()",
            "classes": "errant"
        }))


    # Volunteer Scheduler Involvements
    invs = q.QuerySql("""SELECT OrganizationId as id, OrganizationName as name FROM Organizations WHERE RegistrationTypeId = 22;""")
    for i in invs:
        if model.InOrg(pid, i.id):
            Data.results.append(model.DynamicData({
                "path": "/OnlineReg/{}".format(i.id),
                "fa": "calendar-check-o",
                "label": "Manage {} Commitments".format(i.name)
            }))


    # View Facilities Tickets
    if model.InOrg(pid, 127):
        Data.results.append(model.DynamicData({
            "path": "/PyScript/FacilitiesTicketReport",
            "fa": "paint-brush",
            "label": "View Facilities Issues"
        }))


    # How-To Videos
    Data.results.append(model.DynamicData({
        "path": "https://www.tenth.org/mytenth",
        "fa": "video-camera",
        "label": "How-To Videos"
    }))


    print(model.RenderTemplate(template))

Get()