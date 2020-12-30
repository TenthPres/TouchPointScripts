print "Updating Access Roles...\n"

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


print "\n Add Attendance role\n"
# Add the attendance role for those who are leaders of orgs.  (Note that this doesn't discriminate the type of org.) 
for p in q.QueryList('''
    UserRole <> 3[Attendance]
    AND MemberTypeCodes(  ) IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 1061[Principal], 160[Teacher] )
    AND UserRole NOT IN ( 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    '''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Attendance")