# This is a script to provide different calendar views.

# Pckgd
# Title: Calendar
# Description: Provides month, week, day, and reservables calendar views.
# Updates from: GitHub/TenthPres/TouchPointScripts/Calendar/Calendar.py
# License: AGPL-3.0
# Author: James at Tenth

import calendar
import datetime
# noinspection PyUnresolvedReferences
from clr import Convert
# noinspection PyUnresolvedReferences
from System import DateTime

global model, Data, q

def get_events(dt):
    return q.QuerySql("""
    SELECT 
        m.MeetingDate, 
        m.MeetingEnd, 
        COALESCE(NULLIF(m.Description,''), o.organizationName) as MeetingName, 
        m.MeetingId,
        1 * o.ShowInSites as Featured
    FROM Meetings m
    LEFT JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    
    WHERE m.MeetingDate < DATEADD(day, 1, '{0}') 
    AND COALESCE(m.MeetingEnd, m.MeetingDate) > '{0}'
    AND m.Canceled = 0
    ORDER BY MeetingDate, o.DivisionId
""".format(dt))

def get_reservables():
    # noinspection SqlResolve
    return q.QuerySql("""
    SELECT ReservableId,
    ParentId,
    COALESCE(BadgeColor, '#153aa8') as Color,
    Name,
    Description,
    IsReservable,
    IsEnabled,
    IsCountable,
    Quantity
    FROM Reservable
    WHERE IsDeleted = 0
        -- AND ReservableTypeId = 1
        AND IsEnabled = 1
        
    ORDER BY ReservableTypeId, Name
    ;
""")


def get_reservations(dt):
    return q.QuerySql("""
    -- Room things
    SELECT  
        rb.ReservableId,
        rv.MeetingStart,
        COALESCE(rv.MeetingEnd, rv.MeetingStart) as MeetingEnd, 
        COALESCE(NULLIF(rv.SetupMinutes, ''), 0) as SetupMinutes,
        COALESCE(NULLIF(rv.TeardownMinutes, ''), 0) as TeardownMinutes,
        COALESCE(NULLIF(m.Description, ''), o.OrganizationName) as Name,
        0 as Quantity,
        m.MeetingId,
        o.LeaderName
    INTO #reservables
    FROM Reservations rv
        JOIN Reservable rb ON rv.ReservableId = rb.ReservableId
        JOIN Meetings m ON rv.MeetingId = m.MeetingId
        JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    WHERE rv.MeetingId IS NOT NULL 
        AND rv.MeetingEnd > '{0}'
        AND rv.MeetingStart < DATEADD(day, 1, '{0}');
    
    -- Returns reservable items (furniture and services, not rooms)
    SELECT 
        ri.ReservableId,
        rv.MeetingStart,
        COALESCE(rv.MeetingEnd, rv.MeetingStart) as MeetingEnd, 
        COALESCE(NULLIF(rv.SetupMinutes, ''), 0) as SetupMinutes,
        COALESCE(NULLIF(rv.TeardownMinutes, ''), 0) as TeardownMinutes,
        COALESCE(NULLIF(m.Description, ''), o.OrganizationName) as Name,
        ri.Quantity,
        m.MeetingId,
        o.LeaderName
    INTO #Jawns
    FROM ReservationItems ri 
        LEFT JOIN Reservations rv ON ri.ReservationId = rv.ReservationId
        JOIN Reservable rb ON ri.ReservableId = rb.ReservableId
        JOIN Meetings m ON rv.MeetingId = m.MeetingId
        JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    WHERE rv.MeetingId IS NOT NULL 
        AND rv.MeetingEnd > '{0}'
        AND rv.MeetingStart < DATEADD(day, 1, '{0}')
    ;
    
    SELECT * FROM #reservables UNION SELECT * FROM #Jawns;
""".format(dt))

def generate_calendar_html(date):
    year = date.year
    month = date.month
    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    month_days = cal.monthdatescalendar(year, month)

    # Compute adjacent months
    prev_month = month - 1
    prev_year = year
    next_month = month + 1
    next_year = year

    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    if next_month == 13:
        next_month = 1
        next_year += 1

    prev_link = "?d=%d-%d" % (prev_year, prev_month)
    next_link = "?d=%d-%d" % (next_year, next_month)
    curr_link = "d=%d-%d-%d" % (date.year, date.month, date.day)

    html = []
    html.append("<style>")
    html.append("table { border-collapse: collapse; width: 100%; }")
    html.append("th, td { border: 1px solid #999; vertical-align: top; width: 14%; }")
    html.append(".feat { font-size: 1.3em; font-weight: bold; }")
    html.append("th { background: #eee; }")
    html.append(".daynum { font-weight: bold; }")
    html.append(".event { margin: 2px 0; padding: 2px; background: #def; border-radius: 3px; }")
    html.append(".nav.cal { display: flex; gap: 1em; }")
    html.append(".nav.cal > * { flex:1; }")
    html.append(".nav-c { text-align:center; }")
    html.append(".nav-r { text-align:right; }")
    html.append("</style>")
    # html.append("<h2>%s %d</h2>" % (calendar.month_name[month], year))
    
    model.Title = "Calendar: %s %d" % (calendar.month_name[month], year)
    model.Header = "%s %d" % (calendar.month_name[month], year)
    
    html.append("<div class='nav cal'>")
    
    html.append("<div class='nav-l'></div>")
    
    html.append("<div class='nav-c'>")
    html.append("<a href='%s'>&laquo; %s %d</a> | " % (prev_link, calendar.month_name[prev_month], prev_year))
    html.append("<strong>%s %d</strong>" % (calendar.month_name[month], year))
    html.append(" | <a href='%s'>%s %d &raquo;</a>" % (next_link, calendar.month_name[next_month], next_year))
    html.append("</div>")
    
    html.append("<div class='nav-r'>")
    html.append("<strong>Month</strong>")
    html.append(" | <a href='?v=w&%s'>Week</a>" % curr_link)
    html.append(" | <a href='?v=d&%s'>Day</a>" % curr_link)
    html.append(" | <a href='?v=r&%s'>Reservables</a>" % curr_link)
    html.append("</div>")
    html.append("</div>")

    
    html.append("<table>")
    html.append("<tr>" + "".join("<th>%s</th>" % dn for dn in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]) + "</tr>")

    for week in month_days:
        html.append("<tr>")
        for day in week:
            events = get_events(day)
            
            if day.month == month:
                html.append("<td>")
            
            else:
                html.append("<td style='background:#f9f9f9; opacity:.5'>")
            
            day_link = "?v=d&d=%d-%d-%d" % (day.year, day.month, day.day)
            html.append("<a class='daynum' href='%s'>%d</div>" % (day_link, day.day))
            for ev in events:
                
                classes = ['event']
                
                if ev.Featured:
                    classes.append('feat')
                
                html.append("<a href='/Meeting/MeetingDetails/%s'>" % ev.MeetingId)
                
                html.append("<div class='%s'>" % ' '.join(classes))
                
                html.append("%s<br>" % ev.MeetingName)
                html.append(("<small>%s - %s</small>" % (
                    ev.MeetingDate.ToString("h:mmtt").replace('M',''),
                    ev.MeetingDate.ToString("h:mmtt").replace('M','') if ev.MeetingEnd is None else ev.MeetingEnd.ToString("h:mmtt").replace('M','')
                )).lower().replace(":00",""))
                
                html.append("</div></a>")
            html.append("</td>")
        html.append("</tr>")

    html.append("</table>")
    return "\n".join(html)


def generate_calendar_vert_html(start_date, day_count):
    """
    Generate an HTML week view calendar with overlap handling,
    horizontal hour/half-hour lines, scrollable, and auto-scroll to 8am.
    """
    start_of_span = start_date
    if day_count % 7 == 0:
        start_of_span = start_date - datetime.timedelta(days=start_date.weekday() + 1 if start_date.weekday() != 6 else 0)
    days = [start_of_span + datetime.timedelta(days=i) for i in range(day_count)]
    
    span_term = "Span"
    span_link = str(day_count)
    if day_count == 14:
        span_term = "Fortnight"
    elif day_count == 7:
        span_term = "Week"
        span_link = 'w'
    elif day_count == 1:
        span_term = "Day"
        span_link = 'd'

    hour_height = 6  # vh per hour
    day_start = 0
    day_end = 24
    
    prev_date = start_date - datetime.timedelta(days=day_count)
    next_date = start_date + datetime.timedelta(days=day_count)
    
    prev_link = "d=%d-%d-%d" % (prev_date.year, prev_date.month, prev_date.day)
    next_link = "d=%d-%d-%d" % (next_date.year, next_date.month, next_date.day)
    curr_link = "d=%d-%d-%d" % (start_date.year, start_date.month, start_date.day)
    
    model.Title =  "Calendar: %s of %s %d, %s" % (span_term, calendar.month_name[start_date.month], start_date.day, start_date.year)

    html = []
    html.append("<style>")
    html.append("div#main { width: 100% !important;}")
    html.append(".week-container { height: calc(100vh - 10em); overflow-y: scroll; border: 1px solid #999; }")
    html.append(".week { display: flex; min-height: %dvh; position: relative; padding-left:3em; }" % ((day_end - day_start) * hour_height))
    html.append(".daycol { flex: 3; border-left: 1px solid #999; position: relative; }")
    html.append(".daycol.sun { flex: 4; }")
    html.append(".dayheader { background: #eee; text-align: center; padding: 4px; font-weight: bold; position: sticky; top: 0; z-index: 2; }")
    html.append(".event { position: absolute; background: #def; border: 1px solid #69c; border-radius: 3px; padding: 2px; font-size: 0.85em; overflow: hidden; }")
    html.append(".feat { font-size: 1.1em; font-weight: bold; }")
    html.append(".timegrid { position: absolute; left: 0; right: 0; border-top: 1px dashed #ccc; font-size: 0.7em; color: #666; }")
    html.append(".nav.cal { display: flex; gap: 1em; }")
    html.append(".nav.cal > * { flex:1; }")
    html.append(".nav-c { text-align:center; }")
    html.append(".nav-r { text-align:right; }")
    html.append("</style>")
    
    html.append("<div class='nav cal'>")
    
    html.append("<div class='nav-l'>")
    html.append("</div>")
    
    html.append("<div class='nav-c'>")
    html.append("<a href='?v=%s&%s'>&laquo; Previous %s</a> | " % (span_link, prev_link, span_term))
    html.append("<strong>%s of %s %d, %s</strong>" % (span_term, calendar.month_name[start_date.month], start_date.day, start_date.year))
    html.append(" | <a href='?v=%s&%s'>Next %s &raquo;</a>"  % (span_link, next_link, span_term))
    html.append("</div>")
    
    html.append("<div class='nav-r'>")
    html.append("<a href='?%s'>Month</a>" % curr_link)
    if day_count == 7:
        html.append(" | <strong>Week</strong>")
    else:
        html.append(" | <a href='?v=w&%s'>Week</a>" % curr_link)
    if day_count == 1:
        html.append(" | <strong>Day</strong>")
    else:
        html.append(" | <a href='?v=d&%s'>Day</a>" % curr_link)
        
    html.append(" | <a href='?v=r&%s'>Reservables</a>" % curr_link)
        
    html.append("</div>")
    
    html.append("</div>")

    html.append("<div class='week-container'>")
    html.append("<div class='week'>")

    # Time grid lines (shared across all days)
    for h in range(day_start, day_end + 1):
        top = (h - day_start) * hour_height
        html.append("<div class='timegrid' style='top:%dvh'>%02d:00</div>" % (top, h))
        # half-hour line
        if h < day_end:
            html.append("<div class='timegrid' style='top:%dvh'></div>" % (top + hour_height // 2))

    for day in days:
        events = get_events(day)
        events = sorted(events, key=lambda e: (e.MeetingDate, e.MeetingEnd or e.MeetingDate))
        
        day_c = Convert(day, DateTime)
        tom_c = day_c.AddDays(1)

        # Allocate lanes for overlaps
        lanes = []
        event_positions = {}
        for ev in events:
            placed = False
            for lane_index, lane in enumerate(lanes):
                last = lane[-1]
                if last.MeetingEnd <= ev.MeetingDate:
                    lane.append(ev)
                    event_positions[ev.MeetingId] = lane_index
                    placed = True
                    break
            if not placed:
                lanes.append([ev])
                event_positions[ev.MeetingId] = len(lanes) - 1
        lane_count = max(1, len(lanes))

        html.append("<div class='daycol %s'>" % calendar.day_abbr[day.weekday()].lower())
        html.append("<div class='dayheader'>%s<br>%d</div>" % (calendar.day_abbr[day.weekday()], day.day))

        for ev in events:
            start_hour = 0 if ev.MeetingDate < day_c else ev.MeetingDate.Hour + ev.MeetingDate.Minute / 60.0
            end_hour = 24 if ev.MeetingEnd > tom_c else (ev.MeetingEnd.Hour + ev.MeetingEnd.Minute / 60.0) if ev.MeetingEnd else start_hour

            if start_hour < day_start: start_hour = day_start
            if end_hour > day_end: end_hour = day_end

            top = (start_hour - day_start) * hour_height
            height = (end_hour - start_hour) * hour_height

            lane_index = event_positions[ev.MeetingId]
            width = 100.0 / lane_count
            left = lane_index * width

            classes = ['event']
            if ev.Featured:
                classes.append('feat')

            html.append("<a href='/Meeting/MeetingDetails/%s' title=\"%s\">" % (ev.MeetingId, ev.MeetingName))
            html.append("<div class='%s' style='top:%dvh; height:%dvh; left:%.2f%%; width:%.2f%%'>" % (
                ' '.join(classes), top, height, left, width))
            html.append("%s<br><small>%s - %s</small>" % (
                ev.MeetingName,
                ev.MeetingDate.ToString("h:mmtt").lower().replace(":00","").replace('m',''),
                ev.MeetingEnd.ToString("h:mmtt").lower().replace(":00","").replace('m','') if ev.MeetingEnd else ""
            ))
            html.append("</div></a>")

        html.append("</div>")  # end daycol

    html.append("</div></div>")  # end week and container
    
    # JavaScript to scroll to 8am
    html.append("<script>")
    html.append("window.addEventListener('load', function(){")
    html.append("  var container = document.querySelector('.week-container');")
    html.append("  if(container){ container.scrollTop = container.firstElementChild.clientHeight / 4; }")
    html.append("});")
    html.append("</script>")
    
    return "\n".join(html)

def generate_room_gantt_html(date):
    reservables = get_reservables()
    reservations = get_reservations(date)
    
    hour_width = 6  # vw per hour
    total_hours = 25

    reservable_dict = {r.ReservableId: r for r in reservables}
    children = {r.ReservableId: [] for r in reservables}
    for r in reservables:
        if r.ParentId in reservable_dict:
            children[r.ParentId].append(r)

    def time_to_vw(dt):
        hour = dt.Hour + dt.Minute / 60.0
        return hour * hour_width
        
    prev_date = date - datetime.timedelta(days=1)
    next_date = date + datetime.timedelta(days=1)
    
    prev_link = "d=%d-%d-%d" % (prev_date.year, prev_date.month, prev_date.day)
    next_link = "d=%d-%d-%d" % (next_date.year, next_date.month, next_date.day)
    curr_link = "d=%d-%d-%d" % (date.year, date.month, date.day)

    model.Title = "Usage for %s %d, %d" % (calendar.month_name[date.month], date.day, date.year)

    html = []
    html.append("<style>")
    html.append(".gantt-wrapper { display: flex; height: calc(100vh - 10em); overflow-y: auto; }")
    html.append(".room-labels { flex: 0 0 15em; border-right: 1px solid #999; background: #f9f9f9; white-space: nowrap; height:fit-content; }")
    html.append(".room-label { padding: 4px; border-bottom: 1px solid #ccc; height: 2em; font-weight: bold; }")
    html.append(".gantt-container { overflow-x: scroll; flex: 1; position: relative; height: fit-content; }")
    html.append(".gantt-chart { position: relative; width: %dvw; }" % (hour_width * (total_hours-1)))
    html.append(".room-row { position: relative; height: 2em; border-bottom: 1px solid #ccc; }")
    html.append(".bar { position: absolute; border-radius: 3px; color: #fff; padding: 2px; font-size: 0.8em; overflow: hidden; white-space: nowrap; line-height:.8em; }")
    html.append(".bar small { opacity:.75; }")
    html.append(".setup { opacity: 0.5; }")
    html.append(".timegrid { position: absolute; top: 0; height: 100%; border-left: 1px dashed #ccc; font-size: 0.7em; color: #666; text-align: center; }")
    
    html.append(".nav.cal { display: flex; gap: 1em; }")
    html.append(".nav.cal > * { flex:1; }")
    html.append(".nav-c { text-align:center; }")
    html.append(".nav-r { text-align:right; }")
    html.append("</style>")
    
    html.append("<div class='nav cal'>")
    
    html.append("<div class='nav-l'></div>")
    
    html.append("<div class='nav-c'>")
    html.append("<a href='?v=r&%s'>&laquo; Previous</a> | " % prev_link)
    html.append("<strong>%s %d, %d</strong>" % (calendar.month_name[date.month], date.day, date.year))
    html.append(" | <a href='?v=r&%s'>Next &raquo;</a>" % next_link)
    html.append("</div>")
    
    html.append("<div class='nav-r'>")
    
    html.append("<a href='?%s'>Month</a>" % curr_link)
    html.append(" | <a href='?v=w&%s'>Week</a>" % curr_link)
    html.append(" | <a href='?v=d&%s'>Day</a>" % curr_link)
    html.append(" | <strong>Reservables</strong>")
    html.append("</div>")
    html.append("</div>")
    
    if len(reservations) == 0:
        html.append("<div class='nav-c'><strong>No Reservations</strong></div>")
        return "\n".join(html)

    html.append("<div class='gantt-wrapper'>")
    
    
    def assign_lanes(reses):
        lanes = []
        for res in reses:
            placed = False
            for lane in lanes:
                if all(res.MeetingStart.AddMinutes(-res.SetupMinutes) >= r.MeetingEnd.AddMinutes(r.TeardownMinutes) or res.MeetingEnd.AddMinutes(res.TeardownMinutes) <= r.MeetingStart.AddMinutes(-r.SetupMinutes) for r in lane):
                    lane.append(res)
                    placed = True
                    break
            if not placed:
                lanes.append([res])
        lane_map = {}
        for i, lane in enumerate(lanes):
            for res in lane:
                lane_map[res] = i
        return lane_map, max(1, len(lanes))
    
    
    def reservable_has_reservations(rsbl):
        if len(rsbl._reservations) > 0:
            return True
        
        for child in children.get(rsbl.ReservableId, []):
            if reservable_has_reservations(child):
                return True
        
        return False
        

    # Room rows and bars
    def render_row(rsbl):
        if not reservable_has_reservations(rsbl):
            return
        
        row_height = rsbl._lanes[1] * 2
        
        html.append("<div class='room-row' style='height:%dem'>" % row_height)
        for res in rsbl._reservations:
            start = res.MeetingStart
            end = res.MeetingEnd
            setup_start = start.AddMinutes(-res.SetupMinutes)
            teardown_end = end.AddMinutes(res.TeardownMinutes)

            l = time_to_vw(start)
            width = time_to_vw(end) - l
            setup_left = time_to_vw(setup_start)
            setup_width = time_to_vw(teardown_end) - setup_left

            color = reservable_dict[res.ReservableId].Color

            html.append("<a href='/Meeting/MeetingDetails/%s'>" % res.MeetingId)
            
            
            lane = rsbl._lanes[0][res]
            top_offset = round(lane / (.01 * rsbl._lanes[1]), 2)
            bot_offset = round(((rsbl._lanes[1] - 1 - lane) / (.01 * rsbl._lanes[1])), 2)

            if res.SetupMinutes > 0 or res.TeardownMinutes > 0:
                html.append("<div class='bar setup' style='left:%.2fvw; width:%.2fvw; background:%s; top:calc(%.2f%% + 1px); bottom:calc(%.2f%% + 1px);'></div>" % (
                    setup_left, setup_width, color, top_offset, bot_offset
                ))

            html.append("<div class='bar' style='left:%.2fvw; width:%.2fvw; background:%s; top:calc(%.2f%% + 1px); bottom:calc(%.2f%% + 1px);' title=\"%s\">%s" % (
                l, width, color, top_offset, bot_offset, res.Name, res.Name
            ))
            lbl = ""
            if res.Quantity > 0:
                lbl = "(%d) " % res.Quantity
            if res.LeaderName is not None:
                lbl = "%s%s" % (lbl, res.LeaderName)
            if lbl != "":
                html.append("<small><br />%s</small>" % lbl)
            html.append("</div>")
            html.append("</a>")
        html.append("</div>")
        
        for child in children.get(rsbl.ReservableId, []):
            render_row(child)
            
    
    for rbl in reservables:
        rbl._reservations = [r for r in reservations if r.ReservableId == rbl.ReservableId]
        rbl._lanes = assign_lanes(rbl._reservations)

    # Static room labels
    html.append("<div class='room-labels'>")
    
    def render_labels(rsbl, depth=0):
        if not reservable_has_reservations(rsbl):
            return
        
        indent = "&nbsp;" * (depth * 4)
        height = rsbl._lanes[1] * 2
        html.append("<div class='room-label' style='height:%dem;'>%s%s</div>" % (height, indent, rsbl.Name))
        for child in children.get(rsbl.ReservableId, []):
            render_labels(child, depth + 1)
            
    
    for rbl in reservables:
        if rbl.ParentId not in reservable_dict:
            render_labels(rbl)
    
    html.append("</div>")

    # Scrollable Gantt chart
    html.append("<div class='gantt-container'>")
    html.append("<div class='gantt-chart'>")

    # Time grid lines
    for h in range(total_hours):
        left = (h - .5) * hour_width
        label = "%02d:00" % (h % 24)
        # lines for halves, labels for wholes.
        html.append("<div class='timegrid' style='left:%.2fvw; width:%.2fvw;'>%s</div>" % (left, hour_width, label))

        # whole hour line
        if h < total_hours:
            half_left = left + hour_width / 2
            html.append("<div class='timegrid' style='left:%.2fvw; width:0; border-left: 1px dashed #ccc;'></div>" % half_left)

    for room in reservables:
        if room.ParentId not in reservable_dict:
            render_row(room)

    html.append("</div></div>")  # end gantt-chart and container
    html.append("</div>")  # end gantt-wrapper
    
    # JavaScript to scroll to 8am
    html.append("<script>")
    html.append("window.addEventListener('load', function(){")
    html.append("  var container = document.querySelector('.gantt-container');")
    html.append("  if(container){ container.scrollLeft = container.firstElementChild.clientWidth / 3; }")
    html.append("});")
    html.append("</script>")

    return "\n".join(html)




if True:

    d = datetime.date.today()
    
    if Data.d != '':
        d = Data.d.split('-')
        if len(d) == 2:
            try:
                d = datetime.date(int(d[0]), int(d[1]), 1)
            except:
                pass
        elif len(d) == 3:
            try:
                d = datetime.date(int(d[0]), int(d[1]), int(d[2]))
            except:
                pass
    
    vi = 0        
    try:
        vi = int(Data.v)
    except:
        pass
    
    if Data.v == 'w':
        vi = 7
        
    elif Data.v == 'd':
        vi = 1
    
    if Data.v == 'r':
        print(generate_room_gantt_html(d))
        
    elif vi > 0:
        print(generate_calendar_vert_html(d, vi))
    
    else:
        print(generate_calendar_html(d))

#
