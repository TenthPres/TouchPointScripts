print "Updating Access Roles...\n"


# ###### ACCESS #######

print " Remove Access role...\n"
# Removes the Access role (and indirectly, all other special roles from anyone who isn't: a leader of an org OR a member
# of Staff or Session or Diaconate or Women's Cmte, or
for p in q.QueryList('''
    (
        IsMemberOf( Org=61[Staff] ) <> 1[True]
        AND IsMemberOf( Org=124[Session] ) <> 1[True]
        AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
        AND IsMemberOf( Org=132[Women's Committee] ) <> 1[True]
        AND OrgSearchMember( OrgType2=51 ) <> 1[True]
        AND MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 160[Teacher] )
        AND UserRole NOT IN ( 8[Finance], 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
        AND EmailAddress <> '**touchpointsoftware.com'
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
    NOT (
        IsMemberOf( Org=61[Staff] ) <> 1[True]
        AND IsMemberOf( Org=124[Session] ) <> 1[True]
        AND IsMemberOf( Org=125[Diaconate] ) <> 1[True]
        AND IsMemberOf( Org=132[Women's Committee] ) <> 1[True]
        AND OrgSearchMember( OrgType2=51 ) <> 1[True]
        AND MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 160[Teacher] )
        AND UserRole NOT IN ( 8[Finance], 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
        AND EmailAddress <> '**touchpointsoftware.com'
    )
    AND NOT UserRole = 2[Access]
'''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Access")


# ###### ORGLEADERONLY #######

print "\n Remove OrgLeadersOnly role\n"
# Remove the OrgLeadersOnly role from Officers and Staff (who have Access role already from above)
for p in q.QueryList('''
    ( 
        IsMemberOf( Org=61[Staff] ) = 1[True]
        OR IsMemberOf( Org=124[Session] ) = 1[True]
        OR IsMemberOf( Org=125[Diaconate] ) = 1[True]
        OR IsMemberOf( Org=132[Women's Committee] ) = 1[True]
        OR OrgSearchMember( OrgType2=51[Parish Council] ) = 1[True] 
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
    AND OrgSearchMember( OrgType2=51[Parish Council] ) <> 1[True] 
    AND EmailAddress <> '*touchpointsoftware.com'
    AND UserRole = 2[Access]
    AND UserRole <> 14[OrgLeadersOnly]
'''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "OrgLeadersOnly")


# ###### ATTENDANCE #######

print "\n Add Attendance role\n"
# Add the attendance role for those who are leaders of involvements.
# (Note that this doesn't discriminate the type of org.)
for p in q.QueryList('''
    UserRole <> 3[Attendance]
    AND MemberTypeCodes(  ) IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 160[Teacher] )
    AND UserRole NOT IN ( 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
'''):
    print "  " + p.Name + "\n"
    model.AddRole(p.PeopleId, "Attendance")

print "\n Remove Attendance role\n"
# Remove the attendance role from someone who is not the leader of an org. 
for p in q.QueryList('''
    UserRole = 3[Attendance]
    AND IsMemberOf( Org=61[Staff] ) <> 1[True]
    AND MemberTypeCodes(  ) NOT IN ( 159[Coordinator], 103[Director], 150[Host], 140[Leader], 160[Teacher] )
    AND UserRole NOT IN ( 9[Developer], 18[Checkin], 46[APIOnly], 47[APIWrite] )
    AND EmailAddress <> '*@touchpointsoftware.com'
'''):
    print "  " + p.Name + "\n"
    model.RemoveRole(p.PeopleId, "Attendance")


# ###### MANAGEGROUPS #######

# Leaders of involvements with a Scheduler registration type (RegistrationTypeId 22) need ManageGroups.
SCHEDULER_LEADERS_SQL = '''
    SELECT DISTINCT om.PeopleId
    FROM OrganizationMembers om
    JOIN Organizations o ON o.OrganizationId = om.OrganizationId
    WHERE o.RegistrationTypeId = 22
      AND o.OrganizationStatusId = 30
      AND om.MemberTypeId IN ( 159, 103, 150, 140, 160 )
      AND om.InactiveDate IS NULL
'''
scheduler_leaders = set(r.PeopleId for r in q.QuerySql(SCHEDULER_LEADERS_SQL))

# Current holders of the ManageGroups role, along with whether they have the Access and OrgLeadersOnly roles.
MANAGEGROUPS_HOLDERS_SQL = '''
    SELECT p.PeopleId, p.Name2 AS Name,
           CASE WHEN EXISTS (
                SELECT 1 FROM UserRole ur2 JOIN Roles r2 ON r2.RoleId = ur2.RoleId
                WHERE ur2.UserId = u.UserId AND r2.RoleName = 'Access'
           ) THEN 1 ELSE 0 END AS HasAccess,
           CASE WHEN EXISTS (
                SELECT 1 FROM UserRole ur3 JOIN Roles r3 ON r3.RoleId = ur3.RoleId
                WHERE ur3.UserId = u.UserId AND r3.RoleName = 'OrgLeadersOnly'
           ) THEN 1 ELSE 0 END AS HasOrgLeadersOnly
    FROM Users u
    JOIN People p ON p.PeopleId = u.PeopleId
    JOIN UserRole ur ON ur.UserId = u.UserId
    JOIN Roles r ON r.RoleId = ur.RoleId
    WHERE r.RoleName = 'ManageGroups'
'''
managegroups_holders = list(q.QuerySql(MANAGEGROUPS_HOLDERS_SQL))
managegroups_holder_ids = set(h.PeopleId for h in managegroups_holders)

print "\n Remove ManageGroups role\n"
# Remove ManageGroups from anyone without the Access role, or who is limited to OrgLeadersOnly and doesn't lead a
# Scheduler involvement.
for h in managegroups_holders:
    if not h.HasAccess or (h.HasOrgLeadersOnly and h.PeopleId not in scheduler_leaders):
        print "  " + h.Name + "\n"
        model.RemoveRole(h.PeopleId, "ManageGroups")
        managegroups_holder_ids.discard(h.PeopleId)

print "\n Add ManageGroups role\n"
# Add ManageGroups for leaders of Scheduler involvements who have Access (the Access role is granted above).
for p in q.QueryList('UserRole = 2[Access]'):
    if p.PeopleId in scheduler_leaders and p.PeopleId not in managegroups_holder_ids:
        print "  " + p.Name + "\n"
        model.AddRole(p.PeopleId, "ManageGroups")


# ###### OFFICER #######

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


# ###### SESSION #######

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


# ###### SESSION+DIACONATE #######

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


# ###### SESSION+WOMENSCMTE #######

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


# ###### SESSION+DIACONATE+WOMENSCMTE #######

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

#
