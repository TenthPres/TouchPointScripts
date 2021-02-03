import math
# You can report summary numbers for any status flag or saved search you have set up with this widget
# Example data is below, to use put the name you want to appear in the widget, followed by the status flag code or saved search name on each line
# You can also use multiple status flag codes in a line by separating them by a comma - this will show the number of people that have ALL of the specified flags
# You can link the number to any url as well with a third parameter

searches = [
    ( "Attenders",
    "have attended any event with by-name attendance in the last 90 days",
    '''
        RecentAttendCount( Days=90 ) > 0
    ''' ),
    
    ( "Givers",
    "have given in the last 90 days",
    '''
        StatusFlag = 'F10: Giver '
    ''' ),
    
    ( "Members",
    "are Communicant or Non-Communicant Members of the church",
    '''
        MemberStatusId IN ( 10[Communicant Member], 12[Presbyter], 35[Non-Communicant Member] )
    ''' ),
]

def Get():
    sets = []
    overlaps = []
    template = Data.HTMLContent
    
    # returns false if n is a number that can be divided by 2.
    def IsExp2(x):
        if x == 0:
            return False
        return (math.log10(x) / math.log10(2)) % 1 == 0
    
    for s in searches:
        set = model.DynamicData()
        set.name = s[0]
        set.description = "People who " + s[1]
        set.count = q.QueryCount(s[2])
        sets.append(set)
        
    for oi in range(3, 2**len(searches)):
        if IsExp2(oi):
            continue  
        # if only three searches, this should only run on 3, 6, 7.

        overlap = model.DynamicData()
        query = []
        setsIncl = []
        descIncl = []
        for si in range(0,len(searches)):
            if oi & 2**si == 2**si:
                setsIncl.append(searches[si][0])
                descIncl.append(searches[si][1])
                query.append("(" + searches[si][2] + ")")
        
        overlap.count = q.QueryCount(" AND ".join(query))
        overlap.sets = "'" + "', '".join(setsIncl) + "'"
        overlap.description = "People who " + " AND ".join(descIncl) + ""
                
        overlaps.append(overlap)
    
    Data.sets = sets
    Data.overlaps = overlaps
    print model.RenderTemplate(template)
Get()