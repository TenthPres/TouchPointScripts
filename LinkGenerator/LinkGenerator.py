# Role=Admin

userP = model.GetPerson(model.UserPeopleId)

if not userP.Users[0].InRole("Admin"):
    print "REDIRECT=/"


if Data.pid is not "" and Data.url is not "":
    
    #print Data.pid
    #print Data.url
    
    print "Authenticated URL:"
    
    print model.GetAuthenticatedUrl(int(Data.pid), Data.url, False)
    

else:
    
    print """
    
    <p>Provide a PeopleId and the destination URL</p>
    
    <form action="" method="get">
    <label for"pid">PeopleId</label>
    <input type="int" name="pid" id="pid" />
    <br />
    
    <label for"url">URL</label>
    <input type="int" name="url" id="url" />
    <br />
    
    <input type="submit" />
    </form>
    
    """