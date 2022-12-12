# noinspection PyUnresolvedReferences
import clr
import math
from pprint import pprint

clr.AddReference('System.Web.Extensions')

model.Title = "Hello!"

def getFamilyType(f):
    ret = "UNKNOWN"
    
    # Marital Status
    if f.MemberCount == 1:
        if f.People[0].IsBusiness:
            return "Business / Entity"
        else:
            return "Single w/o dependents"
    
    elif f.HeadOfHousehold is not None and f.HeadOfHouseholdSpouse is not None and not f.HeadOfHousehold.Deceased and not f.HeadOfHouseholdSpouse.Deceased:
        ret = "Couple"  # the easy case of "couple"
        
    else:
        headAndSpouseCount = 0
        headAndSpouseAliveCount = 0
        for p in f.People:
            if p.FamilyPosition.Code == "Primary":
                headAndSpouseCount += 1
                if not p.Deceased:
                    headAndSpouseAliveCount += 1
        if headAndSpouseCount == 2 and headAndSpouseAliveCount == 1:
            ret = "Widowed"
        elif headAndSpouseCount == 1 and headAndSpouseAliveCount == 1:
            ret = "Single"
        elif headAndSpouseCount == 2 and headAndSpouseAliveCount == 2:
            ret = "Couple"
    
    # Children - lists the youngest group
    hasChildren = False
    for p in f.People:
        if p.Age is not None and p.Age < 13:
            hasChildren = True
            ret += " w/ children"
            break
    
    for p in f.People:
        if p.Age is not None and p.Age >= 13 and p.Age < 18:
            ret += " and teens" if hasChildren else " w/ teens"
            hasChildren = True
            break
        
    for p in f.People:
        if p.FamilyPosition.Code == "Other":
            ret += " and dependent adult" if hasChildren else " w/ dependent adult"
            hasChildren = True
            break
        
    if not hasChildren:
        ret += " w/o dependents"
        
    return ret

if model.CurrentOrgId is not None and Data.CurrentOrgId != '':
    org = model.GetOrganization(model.CurrentOrgId)
    if org is None:
        org = model.GetOrganization(Data.CurrentOrgId)
    
    model.Title = "Demographics: {}".format(org.name)
    

if model.HttpMethod == "get" and q.BlueToolbarCount() > 0:
    
    AgeBins = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    resCodeNoneLabel = "Unknown"
    resCodes = {resCodeNoneLabel: [resCodeNoneLabel, 0]}
    famTypes = {}
    memStats = {}
    famTypesSimplified = {}
    AgeNone = 0
    Count = 0
    
    # iterate across results list
    families = {}
    for p in q.BlueToolbarReport("rand", 2000):
        Count += 1
        
        # Bin the ages
        if p.Age is not None:
            age_bin = int(min([math.floor(p.Age / 10.0), 8]))
            AgeBins[age_bin] += 1
        else:
            AgeNone += 1
        
        # Bin the ResCodes
        resCode = p.ResidentCode or p.Family.ResidentCode or resCodeNoneLabel
        if resCode != resCodeNoneLabel:
            resCode = resCode.Description
        if not resCodes.has_key(resCode):
            resCodes[resCode] = [resCode, 0]
        resCodes[resCode][1] += 1
        
        # Bin the MemberStatus
        memStat = p.MemberStatus.Description
        if not memStats.has_key(memStat):
            memStats[memStat] = [memStat, 0]
        memStats[memStat][1] += 1
        
        
        fid_s = str(p.FamilyId)
        
        if not fid_s in families:
            families[fid_s] = {
                'name': 'The ' + p.Family.HeadOfHousehold.Name + " Family",
                'members': [p]
            }
        else:
            families[fid_s]['members'].append(p)
        
    
    # Family Types
    for fp in families.values():
        
        
        # Bin the FamTypes
        famType = getFamilyType(fp['members'][0].Family)
        if not famTypes.has_key(famType):
            famTypes[famType] = [famType, 0]
        famTypes[famType][1] += len(fp['members'])
        
        famTypeSimplified = famType.replace("teens", "children"
            ).replace("dependent adult", "children"
            ).replace(" and children", ""
            ).replace("children", "dependents"
            ).replace("Widowed", "Single")
            
        if not famTypesSimplified.has_key(famTypeSimplified):
            famTypesSimplified[famTypeSimplified] = [famTypeSimplified, 0]
        famTypesSimplified[famTypeSimplified][1] += 1
    
    
    # standardize the data
    
    AgeBins = [
        ["0-9", AgeBins[0]],
        ["10-19", AgeBins[1]],
        ["20-29", AgeBins[2]],
        ["30-39", AgeBins[3]],
        ["40-49", AgeBins[4]],
        ["50-59", AgeBins[5]],
        ["60-69", AgeBins[6]],
        ["70-79", AgeBins[7]],
        ["80+", AgeBins[8]]
    ]
    resCodes = resCodes.values()
    memStats = memStats.values()
    famTypes = famTypes.values()
    if len(famTypes) > 5:
        famTypes = famTypesSimplified.values()
    
    
    print """
    
<style>
@media print {
body div.container-fluid#main {
    width: 100%!important;
}
}
</style>



<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawAgeHistoChart);
    
    function drawAgeHistoChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Age Group');
        data.addColumn('number', 'People');
        data.addRows(""" + "{}".format(AgeBins) + """),
        options = {
            title: 'Age Distribution',
            bar: {groupWidth: '100%'},
            legend: { position: 'none' },
        };
        
        var view = new google.visualization.DataView(data);
        view.setColumns([0, 1,
           { calc: "stringify",
             sourceColumn: 1,
             type: "string",
             role: "annotation" }]);
    
        var chart = new google.visualization.ColumnChart(document.getElementById('ageHisto'));
    
        chart.draw(view, options);
    }
</script>

<div id="ageHisto" style="width: 100%; height: 500px"></div>

<div><p>""" + "{} {} out of {} not shown due to missing age".format(AgeNone, "person" if AgeNone == 1 else "people", Count) + """</p></div>
    
    """
    
    # MemStatus Chart
    print """
    <script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawResCodeChart);
    
    function drawResCodeChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Member Status');
        data.addColumn('number', 'People');
        data.addRows(""" + "{}".format(memStats) + """),
        options = {
            title: 'Membership Statuses',
            //bar: {groupWidth: '100%'},
            legend: { position: 'none' },
        };
        
        var view = new google.visualization.DataView(data);
        view.setColumns([0, 1,
           { calc: "stringify",
             sourceColumn: 1,
             type: "string",
             role: "annotation" }]);
    
        var chart = new google.visualization.ColumnChart(document.getElementById('memStats'));
    
        chart.draw(view, options);
    }
</script>

<div id="memStats" style="width: 100%; height: 500px"></div>
    """
    
    
    
    
    # ResCode Chart
    print """
    <script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawResCodeChart);
    
    function drawResCodeChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Parish');
        data.addColumn('number', 'People');
        data.addRows(""" + "{}".format(resCodes) + """),
        options = {
            title: 'Parish Distribution',
            //bar: {groupWidth: '100%'},
            legend: { position: 'none' },
        };
        
        var view = new google.visualization.DataView(data);
        view.setColumns([0, 1,
           { calc: "stringify",
             sourceColumn: 1,
             type: "string",
             role: "annotation" }]);
    
        var chart = new google.visualization.ColumnChart(document.getElementById('resCodes'));
    
        chart.draw(view, options);
    }
</script>

<div id="resCodes" style="width: 100%; height: 500px"></div>
    
    """
    




    # FamTypes Chart
    print """
    <script type="text/javascript">
    google.charts.load('current', {'packages':['corechart']});
    google.charts.setOnLoadCallback(drawFamTypeChart);
    
    function drawFamTypeChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Family Types');
        data.addColumn('number', 'People');
        data.addRows(""" + "{}".format(famTypes) + """),
        options = {
            title: 'Family Types',
            //bar: {groupWidth: '100%'},
            legend: { position: 'none' },
        };
        
        var view = new google.visualization.DataView(data);
        view.setColumns([0, 1,
           { calc: "stringify",
             sourceColumn: 1,
             type: "string",
             role: "annotation" }]);
    
        var chart = new google.visualization.ColumnChart(document.getElementById('famTypes'));
    
        chart.draw(view, options);
    }
</script>

<div id="famTypes" style="width: 100%; height: 500px"></div>

<style>
div.box-content > div {
	page-break-inside: avoid;
	text-align: center;
}
div {
</style>
    
    """


    
    
else:
    print """It seems you came across this in a way that won't work.  To view demographics, open an Involvement or a Search.  Then, go to 
    the blue toolbar's &lt;/&gt; menu and select the Demographic Analysis report."""