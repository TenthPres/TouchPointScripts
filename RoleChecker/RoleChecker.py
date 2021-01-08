print "Updating Access Roles...\n"


####### ACCESS #######

print " Remove Access role...\n"
# Removes the Access role (and indrectly, all other special roles from anyone who isn't: a leader of an org OR a member of Staff or Session or Diaconate or Women's Cmte
for p in q.QueryList('''
    (
    	MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 1061[Principal], 160[Teacher] )
    	AND UserRole NOT IN ( 8[Finance], 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    	AND IsMemberOf( Org=61[Staff] ) <> 1[True]
    	AND IsMemberOf( Org=124[Session] ) <> 1[True]
    	AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
    	AND IsMemberOf( Org=132[Women's Committee] ) <> 1[True]
    	AND EmailAddress <> '*touchpointsoftware.com'
    )
    AND UserRole = 2[Access]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Access")
    model.RemoveRole(p.PeopleId, "Edit")
    model.RemoveRole(p.PeopleId, "OrgLeadersOnly")
    model.RemoveRole(p.PeopleId, "Attendance")
    

print "\n Add Access role...\n"
# Adds the access role to leaders.
for p in q.QueryList('''
    NOT 
    (
    	MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 1061[Principal], 160[Teacher] )
    	AND UserRole NOT IN ( 8[Finance], 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    	AND IsMemberOf( Org=61[Staff] ) <> 1[True]
    	AND IsMemberOf( Org=124[Session] ) <> 1[True]
    	AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
    	AND IsMemberOf( Org=132[Women's Committee] ) <> 1[True]
    	AND EmailAddress <> '*touchpointsoftware.com'
    )
    AND NOT UserRole = 2[Access]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Access")
    
    
####### ORGLEADERONLY #######

print "\n Remove OrgLeadersOnly role\n"
# Remove the OrgLeadersOnly role from Officers and Staff (who have Access role already from above)
for p in q.QueryList('''
    ( IsMemberOf( Org=61[Staff] ) = 1[True]
    OR IsMemberOf( Org=124[Session] ) = 1[True]
    OR IsMemberOf( Org=125[Diaconate] ) = 1[True]
    OR IsMemberOf( Org=132[Women's Committee] ) = 1[True]
    )
    AND EmailAddress <> '*touchpointsoftware.com'
    AND UserRole = 14[OrgLeadersOnly]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "OrgLeadersOnly")


print "\n Add OrgLeadersOnly role\n"
# Add OrgLeaderOnly for those who have access role (from above), but aren't staff or officers. 
for p in q.QueryList('''
    UserRole NOT IN ( 8[Finance], 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    AND IsMemberOf( Org=61[Staff] ) <> 1[True]
    AND IsMemberOf( Org=124[Session] ) <> 1[True]
    AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
    AND IsMemberOf( Org=132[Women's Committee] ) <> 1[True]
    AND EmailAddress <> '*touchpointsoftware.com'
    AND UserRole = 2[Access]
    AND UserRole <> 14[OrgLeadersOnly]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "OrgLeadersOnly")
    
    
####### ATTENDANCE #######
    
print "\n Add Attendance role\n"
# Add the attendance role for those who are leaders of orgs.  (Note that this doesn't discriminate the type of org.) 
for p in q.QueryList('''
    UserRole <> 3[Attendance]
    AND MemberTypeCodes(  ) IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 1061[Principal], 160[Teacher] )
    AND UserRole NOT IN ( 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Attendance")
    
print "\n Remove Attendance role\n"
# Remove the attendance role from someone who is not the leader of an org. 
for p in q.QueryList('''
    UserRole = 3[Attendance]
    AND MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 1061[Principal], 160[Teacher] )
    AND UserRole NOT IN ( 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    AND EmailAddress <> '*@touchpointsoftware.com'
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Attendance")


####### OFFICER ####### 
    
print "\n Remove Officer role\n"
# Remove the officer role for those appropriate. 
for p in q.QueryList('''
    (
        (
        	IsMemberOf( Org=124[Session] ) <> 1[True]
        	AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
        )
        OR GenderId <> 1[Male]
    )
    AND UserRole = 51[Officer]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Officer")
    
print "\n Add Officer role\n"
# Add the officer role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) = 1[True]
    	OR IsMemberOf( Org=125[Diaconate] ) = 1[True]
    )
    AND UserRole <> 51[Officer]
    AND GenderId = 1[Male]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Officer")
    
    
####### SESSION #######
    
print "\n Remove Session role\n"
# Remove the session role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) <> 1[True]
    )
    AND UserRole = 52[Session]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Session")
    
print "\n Add Session role\n"
# Add the session role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) = 1[True]
    )
    AND UserRole <> 52[Session]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Session")
    

####### SESSION+DIACONATE #######
    
print "\n Remove Session+Diaconate role\n"
# Remove the Session+Diaconate role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) <> 1[True]
    	AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
    )
    AND UserRole = 53[Session+Diaconate]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Session+Diaconate")
    
print "\n Add Session+Diaconate role\n"
# Add the Session+Diaconate role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) = 1[True]
    	OR IsMemberOf( Org=125[Diaconate] ) = 1[True]
    )
    AND UserRole <> 53[Session+Diaconate]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Session+Diaconate")


####### SESSION+WOMENSCMTE #######
    
print "\n Remove Session+WomensCmte role\n"
# Remove the Session+WomensCmte role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) <> 1[True]
    	AND IsMemberOf( Org=132[Women's Cmte] ) <> 1[True]
    )
    AND UserRole = 54[Session+WomensCmte]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Session+WomensCmte")
    
print "\n Add Session+WomensCmte role\n"
# Add the Session+WomensCmte role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) = 1[True]
    	OR IsMemberOf( Org=132[Women's Cmte] ) = 1[True]
    )
    AND UserRole <> 54[Session+WomensCmte]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Session+WomensCmte")
    


####### SESSION+DIACONATE+WOMENSCMTE #######
    
print "\n Remove Session+Diaconate+WomensCmte role\n"
# Remove the Session+Diaconate+WomensCmte role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) <> 1[True]
    	AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
    	AND IsMemberOf( Org=132[Women's Cmte] ) <> 1[True]
    )
    AND UserRole = 55[Session+Diaconate+WomensCmte]
    '''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Session+Diaconate+WomensCmte")
    
print "\n Add Session+Diaconate+WomensCmte role\n"
# Add the Session+Diaconate+WomensCmte role for those appropriate. 
for p in q.QueryList('''
    (
    	IsMemberOf( Org=124[Session] ) = 1[True]
    	OR IsMemberOf( Org=125[Diaconate] ) = 1[True]
    	OR IsMemberOf( Org=132[Women's Cmte] ) = 1[True]
    )
    AND UserRole <> 55[Session+Diaconate+WomensCmte]
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Session+Diaconate+WomensCmte")