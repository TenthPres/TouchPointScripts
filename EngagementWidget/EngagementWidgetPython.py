# Engagement Widget - Developed by Tenth Presbyterian Church for use with TouchPoint church management software. 
# See https://github.com/TenthPres/TouchPointScripts for license and configuration info. 

import math
from pprint import pprint

searches = [
    # Search #1
    [ "Attenders",
    "have attended any event with by-name attendance in the last 90 days",
    '''
        RecentAttendCount( Days=90 ) > 0
    ''',
    "#00aa00" # optional color
    ],
   

    # Search #2
    [ "Givers",
    "have given in the last 90 days",
    '''
        IsFamilyGiver( Days=90 ) = 1[True]
        AND RecordType = 0[Person]
    ''',
    "#aa0000" # optional color
    ],
  

    # Search #3
    [ "Members",
    "are Communicant or Non-Communicant Members of the church",
    '''
        MemberStatusId IN ( 10[Communicant Member] )
    ''',
    "#0000aa" # optional color
    ],
    
    # You can add additional searches here.  However, the geometry will be complicated, at best. 
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
    
    si = 0
    for s in searches:
        set = model.DynamicData()
        set.name = s[0]
        set.description = "People who " + s[1]
        set.count = q.QueryCount(s[2])
        set.color = s[3] if len(s) > 3 else None
        searches[si].append(set.count)
        sets.append(set)
        si += 1
        
    for oi in range(3, 2**len(searches)):
        if IsExp2(oi):
            continue  
        # if only three searches, this should only run on 3, 5, 6, 7.

        overlap = model.DynamicData()
        query = []
        setsIncl = []
        descIncl = []
        pctsIncl = []
        for si in range(0,len(searches)):
            if oi & 2**si == 2**si:
                setsIncl.append(searches[si][0])
                descIncl.append(searches[si][1])
                pctsIncl.append((searches[si][0], searches[si][-1]))
                query.append("(" + searches[si][2] + ")")
        
        overlap.count = q.QueryCount(" AND ".join(query))
        overlap.sets = "'" + "', '".join(setsIncl) + "'"
        overlap.description = "People who " + " AND ".join(descIncl) + ".<br />This represents: "
        for pi in pctsIncl:
            overlap.description = overlap.description + "{}% of {}  ".format(overlap.count * 100 /pi[1], pi[0])
                
        overlaps.append(overlap)
    
    Data.sets = sets
    Data.overlaps = overlaps
    print model.RenderTemplate(template)
Get()
