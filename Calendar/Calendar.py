import calendar
import datetime
from clr import Convert
from System import DateTime

def get_events(dt):
    return q.QuerySql('''
    SELECT 
        m.MeetingDate, 
        m.MeetingEnd, 
        COALESCE(NULLIF(m.Description,''), o.organizationName) as MeetingName, 
        m.MeetingId,
        1 * o.ShowInSites as Featured
    FROM Meetings m 
    LEFT JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    
    WHERE m.MeetingDate < DATEADD(day, 1, '{0}') AND COALESCE(m.MeetingEnd, m.MeetingDate) > '{0}'
    ORDER BY MeetingDate, o.DivisionId
'''.format(dt))

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
    week_link = "?v=w&d=%d-%d-1" % (date.year, date.month)

    html = []
    html.append("<style>")
    html.append("table { border-collapse: collapse; width: 100%; }")
    html.append("th, td { border: 1px solid #999; vertical-align: top; width: 14%; }")
    html.append(".feat { font-size: 1.3em; font-weight: bold; }")
    html.append("th { background: #eee; }")
    html.append(".daynum { font-weight: bold; }")
    html.append(".event { margin: 2px 0; padding: 2px; background: #def; border-radius: 3px; }")
    html.append(".nav { display: flex; gap: 1em; }")
    html.append(".nav-l, .nav-r { flex:1; }")
    html.append(".nav-r { text-align:right; }")
    html.append("</style>")
    # html.append("<h2>%s %d</h2>" % (calendar.month_name[month], year))
    
    model.Title = "Calendar: %s %d" % (calendar.month_name[month], year)
    model.Header = "%s %d" % (calendar.month_name[month], year)
    
    html.append("<div class='nav'>")
    html.append("<div class='nav-l'>")
    html.append("<a href='%s'>&laquo; %s %d</a> | " % (prev_link, calendar.month_name[prev_month], prev_year))
    html.append("<strong>%s %d</strong>" % (calendar.month_name[month], year))
    html.append(" | <a href='%s'>%s %d &raquo;</a>" % (next_link, calendar.month_name[next_month], next_year))
    html.append("</div>")
    
    html.append("<div class='nav-r'>")
    html.append("<strong>Month</strong>")
    html.append(" | <a href='%s'>Week</a>" % (week_link))
    html.append("</div>")
    html.append("</div>")

    
    html.append("<table>")
    html.append("<tr>" + "".join("<th>%s</th>" % d for d in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]) + "</tr>")

    for week in month_days:
        html.append("<tr>")
        for day in week:
            events = get_events(day)
            
            if day.month == month:
                html.append("<td>")
            
            else:
                html.append("<td style='background:#f9f9f9; opacity:.5'>")
                
            html.append("<div class='daynum'>%d</div>" % day.day)
            for ev in events:
                
                classes = ['event']
                
                if ev.Featured:
                    classes.append('feat')
                
                html.append("<a href='/Meeting/MeetingDetails/%s'>" % ev.MeetingId)
                
                html.append("<div class='%s'>" % ' '.join(classes))
                
                html.append("%s<br>" % ev.MeetingName)
                html.append(("<small>%s - %s</small>" % (
                    ev.MeetingDate.ToString("h:mmtt"),
                    ev.MeetingDate.ToString("h:mmtt") if ev.MeetingEnd is None else ev.MeetingEnd.ToString("h:mmtt")
                )).lower().replace(":00",""))
                
                html.append("</div></a>")
            html.append("</td>")
        html.append("</tr>")

    html.append("</table>")
    return "\n".join(html)


def generate_calendar_week_html(start_date):
    """
    Generate an HTML week view calendar with overlap handling,
    horizontal hour/half-hour lines, scrollable, and auto-scroll to 8am.
    """
    start_of_week = start_date - datetime.timedelta(days=start_date.weekday() + 1 if start_date.weekday() != 6 else 0)
    days = [start_of_week + datetime.timedelta(days=i) for i in range(7)]

    hour_height = 6  # vh per hour
    day_start = 0
    day_end = 24
    
    prev_date = start_date - datetime.timedelta(days=7)
    next_date = start_date + datetime.timedelta(days=7)
    
    prev_link = "?v=w&d=%d-%d-%d" % (prev_date.year, prev_date.month, prev_date.day)
    next_link = "?v=w&d=%d-%d-%d" % (next_date.year, next_date.month, next_date.day)
    month_link = "?d=%d-%d-%d" % (next_date.year, next_date.month, next_date.day)
    
    model.Title =  "Calendar: Week of %s %d, %s" % (calendar.month_name[start_date.month], start_date.day, start_date.year)

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
    html.append(".nav { display: flex; gap: 1em; }")
    html.append(".nav-l, .nav-r { flex:1; }")
    html.append(".nav-c { text-align:center; }")
    html.append(".nav-r { text-align:right; }")
    html.append("</style>")
    
    html.append("<div class='nav'>")
    
    html.append("<div class='nav-l'>")
    html.append("<a href='%s'>&laquo; Previous Week</a> | " % prev_link)
    html.append("<a href='%s'>Next Week &raquo;</a>"  % next_link)
    html.append("</div>")
    
    html.append("<div class='nav-c'>")
    html.append("<strong>Week of %s %d, %s</strong>" % (calendar.month_name[start_date.month], start_date.day, start_date.year))
    html.append("</div>")
    
    html.append("<div class='nav-r'>")
    html.append("<a href='%s'>Month</a>" % (month_link))
    html.append(" | <strong>Week</strong>")
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
            end_hour = 24 if ev.MeetingEnd > tom_c else (ev.MeetingEnd.Hour + ev.MeetingEnd.Minute / 60.0) if ev.MeetingEnd else (start_hour + 1)

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
                ev.MeetingDate.ToString("h:mmtt").lower().replace(":00",""),
                ev.MeetingEnd.ToString("h:mmtt").lower().replace(":00","") if ev.MeetingEnd else ""
            ))
            html.append("</div></a>")

        html.append("</div>")  # end daycol

    html.append("</div></div>")  # end week and container
    
    # JavaScript to scroll to 8am
    html.append("<script>")
    html.append("window.addEventListener('load', function(){")
    html.append("  var container = document.querySelector('.week-container');")
    html.append("  if(container){ container.scrollTop = container.clientHeight / 2; }")
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
    
    if Data.v == 'w':
        print generate_calendar_week_html(d)
    
    else:
        print generate_calendar_html(d)

#
