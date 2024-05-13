def Get():
    # sql = Data.SQLContent
    template = Data.HTMLContent
    # params = { 'pid':  }
    
    pid = model.UserPeopleId
    if pid == 12255: # James's PID
        pid = 18428 # Jamin's PID because it's more useful for testing
    
    Data.results = []
    
    # For Shepherds: see those assigned to them
    shepCnt = q.QuerySqlInt("SELECT COUNT(*) FROM FamilyExtra WHERE Field = 'Shepherd PID' AND IntValue = {}".format(pid))
    if shepCnt > 0:
        Data.results.append(model.DynamicData({
            "path": "/PyScript/AssignShepherd?ShepId={}".format(pid),
            "fa": "users",
            "label": "My Flock"
        }))
        
    
    # Parish Emails
    parishes = [
        {
            "name": "Metro",
            "council": 191,
            "emailList": "f8285d98-15a5-46c7-8edf-35e06a8b2359"
        },
        {
            "name": "North",
            "council": 192,
            "emailList": "f7134258-ad0f-4739-83d7-42e417378f9a"
        },
        {
            "name": "West",
            "council": 193,
            "emailList": "6013e87d-c1de-4007-b54d-efc5e37c4e05"
        },
        {
            "name": "Brandywine",
            "council": 194,
            "emailList": "b9e1b009-a154-4c93-ab9d-275c43f9c7d6"
        },
        {
            "name": "Jersey",
            "council": 195,
            "emailList": "b7750b1b-13c4-4343-8380-c0bdcf4911cd"
        },
        {
            "name": "Non-Res",
            "council": 196
        }
    ]
    for p in parishes:
        if model.InOrg(pid, p['council']):
            if 'emailList' in p:
                Data.results.append(model.DynamicData({
                    "path": "/Email/{}".format(p['emailList']),
                    "fa": "envelope",
                    "label": "Send {} Parish Email".format(p['name'])
                }))




    # How-To Videos
    Data.results.append(model.DynamicData({
        "path": "https://www.tenth.org/mytenth",
        "fa": "video-camera",
        "label": "How-To Videos"
    }))
    
    
    print model.RenderTemplate(template)

Get()
