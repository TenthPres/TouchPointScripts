import calendar
import datetime

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
    
    WHERE m.MeetingDate < DATEADD(day, 1, '{0}') AND m.MeetingEnd > '{0}'
    ORDER BY MeetingDate, o.DivisionId
'''.format(dt))

def generate_calendar_html(year, month):
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

    prev_link = "?year=%d&month=%d" % (prev_year, prev_month)
    next_link = "?year=%d&month=%d" % (next_year, next_month)

    html = []
    html.append("<style>")
    html.append("table { border-collapse: collapse; width: 100%; }")
    html.append("th, td { border: 1px solid #999; vertical-align: top; width: 14%; }")
    html.append(".feat { font-size: 1.3em; font-weight: bold; }")
    html.append("th { background: #eee; }")
    html.append(".daynum { font-weight: bold; }")
    html.append(".event { margin: 2px 0; padding: 2px; background: #def; border-radius: 3px; }")
    html.append("</style>")
    # html.append("<h2>%s %d</h2>" % (calendar.month_name[month], year))
    
    model.Title = "Calendar: %s %d" % (calendar.month_name[month], year)
    model.Header = "%s %d" % (calendar.month_name[month], year)
    
    html.append("<div class='nav'>")
    html.append("<a href='%s'>&laquo; %s %d</a> | " % (prev_link, calendar.month_name[prev_month], prev_year))
    html.append("<strong>%s %d</strong>" % (calendar.month_name[month], year))
    html.append(" | <a href='%s'>%s %d &raquo;</a>" % (next_link, calendar.month_name[next_month], next_year))
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
                
                html.append("<a href='/Meeting/%s'>" % ev.MeetingId)
                
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


if True:

    today = datetime.date.today()
    year = today.year
    month = today.month

    if Data.year != '':
        try:
            year = int(Data.year)
        except:
            pass
    if Data.month != '':
        try:
            month = int(Data.month)
        except:
            pass

    html_calendar = generate_calendar_html(year, month)
    print(html_calendar)
