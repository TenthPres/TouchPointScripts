# roles=Global

# change the above role name to limit who can run this report

emailRecipientQuery = "UserRole = 57"   # Query for who receives the emailed report
emailFromAddress = "go@tenth.org"       # the "reply-to" address of the emailed report
emailFromPeopleId = 22029               # the people ID to associate with the sending emailed report
model.Title = "Global Partner Birthdays and Anniversaries"  # used as email subject

# Determine the range for a birthday or anniversary.  Include those are are:
rangeMin = 30  # at least this many days in the future
rangeMax = 70  # but less than this many days in the future

# That's all the configuration needed.

# ##################################################################################################################

global Data, q

# Birthdays


out = "<h2>Upcoming Birthdays</h2>"
out += "<p>Between {} and {} days in the future</p>".format(rangeMin, rangeMax)
out += "<table><tr><th>Partner</th><th>Birthday</th></tr>"

has = False

for p in q.QueryList('''
    (
        DaysTillBirthday > {}
        AND DaysTillBirthday < {}
    )
    AND FamilyExtraInt( Name='Security Level' ) > 0
'''.format(rangeMin, rangeMax)):

    name = p.Name
    if p.Age < 20:
        name += " (" + str(p.Age + 1) + ")"
    elif p.PeopleId not in [p.Family.HeadOfHouseholdId, p.Family.HeadOfHouseholdSpouseId]:
        name += " (adult child)"

    has = True

    out += "<tr><td><a href=\"{}/Person2/{}\">{}</a></td><td>{}</td></tr>".format(model.CmsHost, p.PeopleId, name,
                                                                                  p.BirthDate.ToString("MMMM d"))

if not has:
    out += "<td colspan=2>None this period</td>"

out += "</table>"


# Anniversaries

out += "<h2>Upcoming Anniversaries</h2>"
out += "<p>Between {} and {} days in the future</p>".format(rangeMin, rangeMax)
out += "<table><tr><th>Partners</th><th>Anniversary</th></tr>"

listedFids = []
has = False

for p in q.QueryList('''
    (
        DaysTillAnniversary > {}
        AND DaysTillAnniversary < {}
    )
    AND FamilyExtraInt( Name='Security Level' ) > 0
'''.format(rangeMin, rangeMax)):

    has = True

    if p.FamilyId in listedFids:
        continue

    listedFids.append(p.FamilyId)

    out += "<tr><td><a href=\"{0}/Person2/{1}\">{2}</a> & <a href=\"{0}/Person2/{3}\">{4}</a></td><td>{5}</td></tr>".format(
        model.CmsHost, p.Family.HeadOfHousehold.PeopleId, p.Family.HeadOfHousehold.Name,
        p.Family.HeadOfHouseholdSpouse.PeopleId, p.Family.HeadOfHouseholdSpouse.Name,
        p.WeddingDate.ToString("MMMM d, yyyy"))

if not has:
    out += "<td colspan=2>None this period</td>"

out += "</table>"

if model.FromMorningBatch or Data.email != '':
    model.Transactional = True
    model.Email(emailRecipientQuery, emailFromPeopleId, emailFromAddress,
                "Global Outreach Automation", model.Title, out)

else:
    print out
