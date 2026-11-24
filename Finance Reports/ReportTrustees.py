import clr
clr.AddReference("System.Core")
from System.Collections.Generic import List
from datetime import date

model.Title = "Trustee Report"
1
currentYear = date.today().year

def MonthNumToString(num):
    names = ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
    return names[num%12]

# ######################## #
#  Worship Attendance YoY  #
# ######################## #

WorshAttendTrendSql = '''

DECLARE @currYear AS Int = YEAR(getdate());
DECLARE @divId AS Int = 11;

select SUM(m.MaxCount) as Total,
    CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+1, m.MeetingDate) AS Date) as Sunday
    into #SundayTotals
    FROM dbo.Meetings m
        JOIN dbo.Organizations o on o.OrganizationId = m.OrganizationId
        JOIN dbo.DivOrg do on do.OrgId = o.OrganizationId
        JOIN dbo.Division d on d.Id = do.DivId
    where do.DivId in (@divId) and YEAR(m.MeetingDate) >= @currYear-4 and m.MeetingDate <= getdate()
    GROUP BY CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+1, m.MeetingDate) AS Date);

WITH DATA AS (select Total, Sunday from #SundayTotals)

SELECT DISTINCT Month(st.Sunday) AS [Mon],
    (SELECT AVG(Total) FROM #SundayTotals sty WHERE Month(sty.Sunday) = month(st.Sunday) AND Year(sty.Sunday) = @currYear) as [y0],
    (SELECT AVG(Total) FROM #SundayTotals sty WHERE Month(sty.Sunday) = month(st.Sunday) AND Year(sty.Sunday) = @currYear-1) as [y1],
    (SELECT AVG(Total) FROM #SundayTotals sty WHERE Month(sty.Sunday) = month(st.Sunday) AND Year(sty.Sunday) = @currYear-2) as [y2],
    (SELECT AVG(Total) FROM #SundayTotals sty WHERE Month(sty.Sunday) = month(st.Sunday) AND Year(sty.Sunday) = @currYear-3) as [y3],
    (SELECT AVG(Total) FROM #SundayTotals sty WHERE Month(sty.Sunday) = month(st.Sunday) AND Year(sty.Sunday) = @currYear-4) as [y4]
FROM #SundayTotals as st

DROP TABLE #SundayTotals
'''

d = []
for row in model.SqlListDynamicData(WorshAttendTrendSql):
    d.append([MonthNumToString(row.Mon), row.y0, row.y1, row.y2, row.y3, row.y4])

Data.WorshAttendTrend = model.JsonSerialize(d)
Data.CurrentYear = currentYear


# ############################### #
#  Worship Attendance by Service  #
# ############################### #


WorshBreakdownTrendSql = '''
DECLARE @startDate AS Date = DATEADD(yy, -3, getdate());
DECLARE @divId AS Int = 11;

select SUM(m.MaxCount) as Total,
    CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+2, m.MeetingDate) AS Date) as Sunday,
    DATEPART(hh, m.MeetingDate) as T,
    o.OrganizationId
    into #SundayTotals
    FROM dbo.Meetings m
        JOIN dbo.Organizations o on o.OrganizationId = m.OrganizationId
        JOIN dbo.DivOrg do on do.OrgId = o.OrganizationId
        JOIN dbo.Division d on d.Id = do.DivId
    where do.DivId in (@divId) and m.MeetingDate >= @startDate AND m.MeetingDate <= getdate()
    GROUP BY CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+2, m.MeetingDate) AS Date), DATEPART(hh, m.MeetingDate), o.OrganizationId;

WITH DATA AS (select Total, Sunday from #SundayTotals)

SELECT DISTINCT st.Sunday AS [date],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 65 AND sty.T = 9) as [morn9],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 65 AND sty.T = 11) as [morn11],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 67 AND (sty.T = 13 OR sty.T = 14)) as [aft1],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 66 AND (sty.T = 17 OR sty.T = 18)) as [eve6],
    (SELECT sum(Total) FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday) AS [tot]

FROM #SundayTotals as st

DROP TABLE #SundayTotals
'''

d = []
for row in model.SqlListDynamicData(WorshBreakdownTrendSql):
    other = row.tot - (row.eve6 or 0) - (row.aft1 or 0) - (row.morn11 or 0) - (row.morn9 or 0)
    if other == 0:
        other = None
    d.append([row.date.ToString("yyyy-MM-dd"), row.morn9, row.morn11, row.aft1, row.eve6, other])

Data.WorshBreakdownTrend = model.JsonSerialize(d)



# ############################### #
#  Livestream Viewers by Service  #
# ############################### #


WorshLivestreamTrendSql = '''
DECLARE @startDate AS Date = DATEADD(yy, -3, getdate());
DECLARE @endDate AS Date = DATEADD(dd, 1, getdate());
DECLARE @divId AS Int = 11;

select SUM(CAST(me.Data as INT)) as Total,
    CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+2, m.MeetingDate) AS Date) as Sunday,
    DATEPART(hh, m.MeetingDate) as T,
    o.OrganizationId
    into #SundayTotals
    FROM dbo.Meetings m
        JOIN dbo.Organizations o on o.OrganizationId = m.OrganizationId
        JOIN dbo.DivOrg do on do.OrgId = o.OrganizationId
        JOIN dbo.Division d on d.Id = do.DivId
        LEFT JOIN MeetingExtra me ON m.MeetingId = me.MeetingId AND 'LivestreamConcur' = me.Field
    WHERE do.DivId in (@divId) and m.MeetingDate >= @startDate AND m.MeetingDate <= @endDate
    GROUP BY CAST(DATEADD(dd, DATEPART(dw, m.MeetingDate)*-1+2, m.MeetingDate) AS Date), DATEPART(hh, m.MeetingDate), o.OrganizationId;

WITH DATA AS (select Total, Sunday from #SundayTotals)

SELECT DISTINCT st.Sunday AS [date],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 65 AND sty.T = 9) as [morn9],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 65 AND sty.T = 11) as [morn11],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 67 AND (sty.T = 13 OR sty.T = 14)) as [aft1],
    (SELECT Total FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday AND sty.OrganizationId = 66 AND (sty.T = 17 OR sty.T = 18)) as [eve6],
    (SELECT sum(Total) FROM #SundayTotals sty WHERE sty.Sunday = st.Sunday) AS [tot]

FROM #SundayTotals as st

DROP TABLE #SundayTotals
'''

d = []
for row in model.SqlListDynamicData(WorshLivestreamTrendSql):
    if row.tot is None:
        row.tot = 0
    other = row.tot - (row.eve6 or 0) - (row.aft1 or 0) - (row.morn11 or 0) - (row.morn9 or 0)
    if other == 0:
        other = None
    d.append([row.date.ToString("yyyy-MM-dd"), row.morn9, row.morn11, row.aft1, row.eve6, other])

Data.WorshLivestreamTrend = model.JsonSerialize(d)









# ################### #
#  Finance Condition  #
# ################### #

if ("Finance" in model.GetPerson(model.UserPeopleId).Users[0].Roles):

# ################ #
#  Giving by Type  #
# ################ #

    # The type of a gift is no longer held in Contribution.ContributionTypeId; it is the type of the bundle
    # the gift was entered in (lookup.BundleHeaderTypes), as used by the Intacct export.  The series are built
    # from whatever types have gifts, so new bundle types show up without editing this script.
    GivingTrendSql = '''
    DECLARE @startDate AS Date = DATEADD(yy, -1, getdate());

    SELECT  CAST(DATEADD(dd, DATEPART(dw, c.ContributionDate)*-1+1, c.ContributionDate) AS Date) as date,
            COALESCE(bht.Description, bht.Code, 'Other') as Typ,
            COUNT(c.ContributionId) as cnt,
            SUM(c.ContributionAmount) as amt
        FROM Contribution c
            LEFT JOIN BundleDetail bd ON bd.ContributionId = c.ContributionId
            LEFT JOIN BundleHeader bh ON bh.BundleHeaderId = bd.BundleHeaderId
            LEFT JOIN lookup.BundleHeaderTypes bht ON bht.Id = bh.BundleHeaderTypeId
        WHERE c.ContributionStatusId = 0 AND c.ContributionTypeId NOT IN (6, 99) AND c.ContributionDate >= @startDate
        GROUP BY CAST(DATEADD(dd, DATEPART(dw, c.ContributionDate)*-1+1, c.ContributionDate) AS Date), COALESCE(bht.Description, bht.Code, 'Other')
    '''
    gTypeTotals = {}
    gWeeks = {}
    for row in model.SqlListDynamicData(GivingTrendSql):
        wk = row.date.ToString("yyyy-MM-dd")
        if wk not in gWeeks:
            gWeeks[wk] = {}
        gWeeks[wk][row.Typ] = (row.cnt, row.amt)
        gTypeTotals[row.Typ] = gTypeTotals.get(row.Typ, 0) + (row.amt or 0)

    gTypes = sorted(gTypeTotals.keys(), key=lambda t: -gTypeTotals[t])
    dTy = []
    dAm = []
    for wk in sorted(gWeeks.keys(), reverse=True):
        dTy.append([wk] + [gWeeks[wk][t][0] if t in gWeeks[wk] else None for t in gTypes])
        dAm.append([wk] + [gWeeks[wk][t][1] if t in gWeeks[wk] else None for t in gTypes])

    Data.GivingTypeNames = model.JsonSerialize(gTypes)
    Data.GivingTypeTrend = model.JsonSerialize(dTy)
    Data.GivingAmtTrend = model.JsonSerialize(dAm)


# ################ #
#  Giving History  #
# ################ #


    GivingHistSql = '''
    DECLARE @currYear AS Int = YEAR(getdate());

    SELECT  sum(ContributionAmount) as amt,
            ContributionTypeId,
            CAST(DATEADD(dd, DATEPART(dd, ContributionDate)*-1+1, ContributionDate) AS Date) as month
        into #GivingHist
        FROM Contribution
        WHERE ContributionStatusId = 0 AND ContributionTypeId NOT IN (6, 99) AND year(ContributionDate) >= @currYear-3
        GROUP BY ContributionTypeId, CAST(DATEADD(dd, DATEPART(dd, ContributionDate)*-1+1, ContributionDate) AS Date)
        ORDER BY Month;

    WITH DATA AS (select amt, ContributionTypeId, month from #GivingHist)


    SELECT DISTINCT Month(gh.month) AS [Mon],
        (SELECT SUM(Amt) FROM #GivingHist ghy WHERE Month(ghy.month) = month(gh.month) AND Year(ghy.month) = @currYear) as [y0],
        (SELECT SUM(Amt) FROM #GivingHist ghy WHERE Month(ghy.month) = month(gh.month) AND Year(ghy.month) = @currYear-1) as [y1],
        (SELECT SUM(Amt) FROM #GivingHist ghy WHERE Month(ghy.month) = month(gh.month) AND Year(ghy.month) = @currYear-2) as [y2],
        (SELECT SUM(Amt) FROM #GivingHist ghy WHERE Month(ghy.month) = month(gh.month) AND Year(ghy.month) = @currYear-3) as [y3]
    FROM #GivingHist as gh

    DROP TABLE #GivingHist
    '''

    dHist = []
    for row in model.SqlListDynamicData(GivingHistSql):
        dHist.append([MonthNumToString(row.Mon), row.y0, row.y1, row.y2, row.y3])

    Data.GivingHist = model.JsonSerialize(dHist)


# ############################# #
#  Giving by Membership Status  #
# ############################# #


    GivingMemberHistoryCnt = '''
    DECLARE @currYear AS Int = YEAR(getdate());

    SELECT  DATEPART(year, ContributionDate) as year,
            -- sum(ContributionAmount) as amt,
            COUNT(DISTINCT c.PeopleId) as cnt,
            ms.Code as MemStatus
        INTO #ParishGiving
        FROM Contribution c
            JOIN People p ON c.PeopleId = p.PeopleId
            LEFT JOIN lookup.MemberStatus ms ON p.memberStatusId = ms.Id
        WHERE ContributionStatusId = 0 AND ContributionTypeId NOT IN (6, 99) AND year(ContributionDate) >= @currYear-15
        GROUP BY DATEPART(year, ContributionDate), ms.Code
        ORDER BY year;

    WITH DATA AS (select cnt, year, MemStatus from #ParishGiving)


    SELECT [year], [Pending], [Member], [Assoc], [Previous], [Non], [Pres]
    FROM #ParishGiving as pg
    PIVOT (
         -- SUM(Amt)
         SUM(cnt)
         FOR MemStatus IN ([Pending], [Member], [Assoc], [Previous], [Non], [Pres])
    ) AS PT

    DROP TABLE #ParishGiving
    '''

    dMemGivCnt = []
    for row in model.SqlListDynamicData(GivingMemberHistoryCnt):
        dMemGivCnt.append([row.year, row.Pending, row.Member, row.Assoc, row.Previous, row.Non, row.Pres])

    Data.GivingMemberHistoryCnt = model.JsonSerialize(dMemGivCnt)


# ########################## #
#  Giving by Parish - Count  #
# ########################## #


    GivingParishHistoryCnt = '''
    DECLARE @currYear AS Int = YEAR(getdate());

    SELECT  DATEPART(year, ContributionDate) as year,
            -- sum(ContributionAmount) as amt,
            COUNT(DISTINCT c.PeopleId) as cnt,
            rc.Code as ResCode
        INTO #ParishGiving
        FROM Contribution c
            JOIN People p ON c.PeopleId = p.PeopleId
            LEFT JOIN lookup.ResidentCode rc ON p.PrimaryResCode = rc.Id
        WHERE ContributionStatusId = 0 AND ContributionTypeId NOT IN (6, 99) AND year(ContributionDate) >= @currYear-15
        GROUP BY DATEPART(year, ContributionDate), rc.Code
        ORDER BY year;

    WITH DATA AS (select cnt, year, ResCode from #ParishGiving)


    SELECT [year], [M], [N], [W], [B], [NJ], [NR], [?] as Unk
    FROM #ParishGiving as pg
    PIVOT (
        -- SUM(Amt)
        SUM(cnt)
        FOR ResCode IN ([M], [N], [W], [B], [NJ], [NR], [?])
    ) AS PT

    DROP TABLE #ParishGiving
    '''

    dParGivCnt = []
    dParGivPct = []
    for row in model.SqlListDynamicData(GivingParishHistoryCnt):
        sum = row.M + row.N + row.W + row.B + row.NJ + row.NR + row.Unk
        dParGivCnt.append([row.year, row.M, row.N, row.W, row.B, row.NJ, row.NR, row.Unk])
        dParGivPct.append([row.year, 1.0*row.M/sum, 1.0*row.N/sum, 1.0*row.W/sum, 1.0*row.B/sum, 1.0*row.NJ/sum, 1.0*row.NR/sum, 1.0*row.Unk/sum])

    Data.GivingParishHistoryCnt = model.JsonSerialize(dParGivCnt)
    Data.GivingParishHistoryPct = model.JsonSerialize(dParGivPct)


# ########################### #
#  Giving by Parish - Amount  #
# ########################### #


    GivingParishHistoryAmt = '''
        DECLARE @currYear AS Int = YEAR(getdate());

    SELECT  DATEPART(year, ContributionDate) as year,
            sum(ContributionAmount) as amt,
            -- COUNT(DISTINCT c.PeopleId) as cnt,
            rc.Code as ResCode
        INTO #ParishGiving
        FROM Contribution c
            JOIN People p ON c.PeopleId = p.PeopleId
            LEFT JOIN lookup.ResidentCode rc ON p.PrimaryResCode = rc.Id
        WHERE ContributionStatusId = 0 AND ContributionTypeId NOT IN (6, 99) AND year(ContributionDate) >= @currYear-15
        GROUP BY DATEPART(year, ContributionDate), rc.Code
        ORDER BY year;

    WITH DATA AS (select amt, year, ResCode from #ParishGiving)


    SELECT [year], [M], [N], [W], [B], [NJ], [NR], [?] as Unk
    FROM #ParishGiving as pg
    PIVOT (
        SUM(Amt)
        -- SUM(cnt)
        FOR ResCode IN ([M], [N], [W], [B], [NJ], [NR], [?])
    ) AS PT

    DROP TABLE #ParishGiving
    '''

    dParGivAmt = []
    dParGivAmtInf = []
    for row in model.SqlListDynamicData(GivingParishHistoryAmt):
        dParGivAmt.append([(row.year or 0), (row.M or 0), (row.N or 0), (row.W or 0), (row.B or 0), (row.NJ or 0), (row.NR or 0), (row.Unk or 0)])
        inf = 1.02 ** (currentYear - row.year - 1)
        dParGivAmtInf.append([row.year,
            (row.M or 0) * inf,
            (row.N or 0) * inf,
            (row.W or 0) * inf,
            (row.B or 0) * inf,
            (row.NJ or 0) * inf,
            (row.NR or 0) * inf,
            (row.Unk or 0) * inf])


    Data.GivingParishHistoryAmt = model.JsonSerialize(dParGivAmt)
    Data.GivingParishHistoryAmtInf = model.JsonSerialize(dParGivAmtInf)


print '''
<style>
@media print {
body div.container-fluid#main {
    width: 100%!important;
}
}
</style>

'''



template = """

<h2>Attendance</h2>

<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawAttTrendChart);

    function drawAttTrendChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Month');
        data.addColumn('number', {{{CurrentYear}}});
        data.addColumn('number', {{{CurrentYear}}}-1);
        data.addColumn('number', {{{CurrentYear}}}-2);
        data.addColumn('number', {{{CurrentYear}}}-3);
        data.addColumn('number', {{{CurrentYear}}}-4);
        data.addRows({{{WorshAttendTrend}}}),
        options = {
            title: 'Average Total Weekly Worship Attendance Year over Year',
            curveType: 'function',
            legend: { position: 'bottom' },
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.LineChart(document.getElementById('attTrends'));

    chart.draw(data, options);
    }
</script>

<div id="attTrends" style="width: 100%; height: 500px"></div>



<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawAttBreakdownChart);

    function drawAttBreakdownChart() {
        var data = new google.visualization.DataTable(),
            d = {{{WorshBreakdownTrend}}};
        data.addColumn('date', 'Date');
        data.addColumn('number', 'Morning (9am)');
        data.addColumn('number', 'Morning (11am)');
        data.addColumn('number', 'Afternoon');
        data.addColumn('number', 'Evening');
        data.addColumn('number', 'Other');
        for (const ri in d) {
            d[ri][0] = new Date(d[ri][0]);
        }
        data.addRows(d);
        var options = {
            title: 'Breakdown of Worship Attendance by Service',
            isStacked: true,
            legend: { position: 'bottom' },
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('attBreakdown'));

    chart.draw(data, options);
    }
</script>

<div id="attBreakdown" style="width: 100%; height: 500px"></div>



<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawAttLivestreamChart);

    function drawAttLivestreamChart() {

        var data = new google.visualization.DataTable(),
            d = {{{WorshLivestreamTrend}}};
        data.addColumn('date', 'Date');
        data.addColumn('number', 'Morning (9am)');
        data.addColumn('number', 'Morning (11am)');
        data.addColumn('number', 'Afternoon');
        data.addColumn('number', 'Evening');
        data.addColumn('number', 'Other');
        for (const ri in d) {
            d[ri][0] = new Date(d[ri][0]);
        }
        data.addRows(d);
        var options = {
            title: 'Livestream Viewers by Service (simultaneous, 30-minutes after start; Counting method began in 2023)',
            isStacked: true,
            legend: { position: 'bottom' },
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('attLivestream'));

    chart.draw(data, options);
    }
</script>

<div id="attLivestream" style="width: 100%; height: 500px"></div>



<h2>General Giving</h2>

<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivHistChart);

    function drawGivHistChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Month');
        data.addColumn('number', {{{CurrentYear}}});
        data.addColumn('number', {{{CurrentYear}}}-1);
        data.addColumn('number', {{{CurrentYear}}}-2);
        data.addColumn('number', {{{CurrentYear}}}-3);
        data.addRows({{{GivingHist}}}),
        options = {
            title: 'Total Monthly Giving Year over Year',
            curveType: 'function',
            legend: { position: 'bottom' },
            vAxis: {format: 'currency'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.LineChart(document.getElementById('givHist'));

    chart.draw(data, options);
    }
</script>

<div id="givHist" style="width: 100%; height: 500px"></div>


<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingTypeChart);

    function drawGivingTypeChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingTypeTrend}}};
        data.addColumn('date', 'Date');
        for (const n of {{{GivingTypeNames}}}) {
            data.addColumn('number', n);
        }
        for (const ri in d) {
            d[ri][0] = new Date(d[ri][0]);
        }
        data.addRows(d);
        var options = {
            title: 'Numbers of Gifts Received by Type',
            isStacked: true,
            legend: { position: 'bottom' },
            vAxis: {viewWindow: {min: 0}},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('givingTypes'));

    chart.draw(data, options);
    }
</script>

<div id="givingTypes" style="width: 100%; height: 500px"></div>


<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingAmtChart);

    function drawGivingAmtChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingAmtTrend}}};
        data.addColumn('date', 'Date');
        for (const n of {{{GivingTypeNames}}}) {
            data.addColumn('number', n);
        }
        for (const ri in d) {
            d[ri][0] = new Date(d[ri][0]);
        }
        data.addRows(d);
        var options = {
            title: 'Total Amounts of Gifts Received by Type',
            isStacked: true,
            legend: { position: 'bottom' },
            vAxis: {format: 'currency', viewWindow: {min: 0}},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('givingAmts'));

    chart.draw(data, options);
    }
</script>

<div id="givingAmts" style="width: 100%; height: 500px"></div>


<h2>Givers by Membership Status</h2>

<p>Note: The membership status used for a giving record is the <b>current</b> status.  Therefore, if someone was a member but is no more, their prior giving would appear under their current status.</p>



<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingMemberCntChart);

    function drawGivingMemberCntChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingMemberHistoryCnt}}};
        data.addColumn('string', 'Year');
        data.addColumn('number', 'Pending');
        data.addColumn('number', 'Member');
        data.addColumn('number', 'Assoc');
        data.addColumn('number', 'Previous');
        data.addColumn('number', 'Non');
        data.addColumn('number', 'Pres');
        for (const ri in d) {
            d[ri][0] = d[ri][0].toString();
        }
        data.addRows(d);
        var options = {
            title: 'Unique Givers by Membership Status',
            isStacked: true,
            legend: { position: 'bottom' },
            //vAxis: {format: 'currency'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('memberGivingCnt'));

    chart.draw(data, options);
    }
</script>

<div id="memberGivingCnt" style="width: 100%; height: 500px"></div>


<h2>Giving by Parish</h2>

<p>Note: The Parish used for a giving record is the <b>current</b> Parish on the donor's Person record.  Therefore, if someone gives and then moves, their prior giving would appear in their current Parish.</p>



<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingParishCntChart);

    function drawGivingParishCntChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingParishHistoryCnt}}};
        data.addColumn('string', 'Year');
        data.addColumn('number', 'M');
        data.addColumn('number', 'N');
        data.addColumn('number', 'W');
        data.addColumn('number', 'B');
        data.addColumn('number', 'NJ');
        data.addColumn('number', 'NR');
        data.addColumn('number', 'Unk');
        for (const ri in d) {
            d[ri][0] = d[ri][0].toString();
        }
        data.addRows(d);
        var options = {
            title: 'Unique Givers by Parish',
            isStacked: true,
            legend: { position: 'bottom' },
            //vAxis: {format: 'currency'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('parishGivingCnt'));

    chart.draw(data, options);
    }
</script>

<div id="parishGivingCnt" style="width: 100%; height: 500px"></div>





<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingParishPctChart);

    function drawGivingParishPctChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingParishHistoryPct}}};
        data.addColumn('string', 'Year');
        data.addColumn('number', 'M');
        data.addColumn('number', 'N');
        data.addColumn('number', 'W');
        data.addColumn('number', 'B');
        data.addColumn('number', 'NJ');
        data.addColumn('number', 'NR');
        data.addColumn('number', 'Unk');
        for (const ri in d) {
            d[ri][0] = d[ri][0].toString();
        }
        data.addRows(d);
        var options = {
            title: 'Percentage of Givers by Parish',
            isStacked: true,
            legend: { position: 'bottom' },
            vAxis: {format:'#,###%'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('parishGivingPct'));

    chart.draw(data, options);
    }
</script>

<div id="parishGivingPct" style="width: 100%; height: 500px"></div>





<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingParishAmtChart);

    function drawGivingParishAmtChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingParishHistoryAmt}}};
        data.addColumn('string', 'Year');
        data.addColumn('number', 'M');
        data.addColumn('number', 'N');
        data.addColumn('number', 'W');
        data.addColumn('number', 'B');
        data.addColumn('number', 'NJ');
        data.addColumn('number', 'NR');
        data.addColumn('number', 'Unk');
        for (const ri in d) {
            d[ri][0] = d[ri][0].toString();
        }
        data.addRows(d);
        var options = {
            title: "Total Giving by Parish",
            isStacked: true,
            legend: { position: 'bottom' },
            vAxis: {format: 'currency'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('parishGivingAmt'));

    chart.draw(data, options);
    }
</script>

<div id="parishGivingAmt" style="width: 100%; height: 500px"></div>

<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawGivingParishAmtInfChart);

    function drawGivingParishAmtInfChart() {
        var data = new google.visualization.DataTable(),
            d = {{{GivingParishHistoryAmtInf}}};
        data.addColumn('string', 'Year');
        data.addColumn('number', 'M');
        data.addColumn('number', 'N');
        data.addColumn('number', 'W');
        data.addColumn('number', 'B');
        data.addColumn('number', 'NJ');
        data.addColumn('number', 'NR');
        data.addColumn('number', 'Unk');
        for (const ri in d) {
            d[ri][0] = d[ri][0].toString();
        }
        data.addRows(d);
        var options = {
            title: "Total Giving by Parish - Inflation adjusted to " + ({{{CurrentYear}}} - 1) + " dollars, using average of 2%/year",
            isStacked: true,
            legend: { position: 'bottom' },
            vAxis: {format: 'currency'},
            chartArea: {
                width: "80%",
                height: "80%"
            }
        };

    var chart = new google.visualization.ColumnChart(document.getElementById('parishGivingAmtInf'));

    chart.draw(data, options);
    }
</script>

<div id="parishGivingAmtInf" style="width: 100%; height: 500px"></div>




"""

print model.RenderTemplate(template, Data)
