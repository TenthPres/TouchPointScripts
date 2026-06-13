mainQuery = model.SqlContent('BackgroundChecks-Status')

model.Title = "Background Checks Stats"

mainQuery = mainQuery.replace("-- INTO ", "INTO ")

sql = """
{0};

SELECT  
    IIF(Status = 'Invalid', 'Invalid', 'Valid') as status,
    IIF(Employee = 'Employee', 'Employee', 'Volunteer') as employee,
    IIF(TrainAssign > Training OR (TrainAssign IS NOT NULL AND Training IS NULL), 'Assigned', 
        IIF(Training IS NULL OR Training < GETDATE(), 'Invalid', 'Valid')
    ) as training
INTO #summary
FROM #status s;

SELECT COUNT(*) as count,
    status as [BackgroundCheck],
    employee,
    training as [Training]
FROM #summary
GROUP BY status, employee, training

""".format(mainQuery)


d = []
for row in model.SqlListDynamicData(sql):
    d.append({
        "count": row.count,
        "Employee": row.employee, 
        "Status": row.BackgroundCheck, 
        "Training": row.Training, 
        })
        

print """
<div>
  <label for="employeeFilter">Filter by Employment: </label>
  <select id="employeeFilter">
    <option value="all">All</option>
  </select>
</div>
<div id="chart_div"></div>
"""

print """
<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">

let data = {0};""".format(model.JsonSerialize(d))

print """

// Load the Google Charts package
google.charts.load('current', { packages: ['corechart', 'bar'] });
google.charts.setOnLoadCallback(drawChart);

let employeeFilter = document.getElementById('employeeFilter');

// Populate employee filter dropdown
let employees = [...new Set(data.map(item => item.Employee))]; // Unique employees
employees.forEach(emp => {
    let option = document.createElement('option');
    option.value = emp;
    option.text = emp;
    employeeFilter.add(option);
});

// Function to filter and aggregate data
function filterData(employee) {
    let filteredData = employee === 'all' ? data : data.filter(d => d.Employee === employee);

    // Aggregate data for status and training
    let statusCounts = {};
    let trainingCounts = {};

    for (let i = 0; i < filteredData.length; ++i) {
        d = filteredData[i];

        // Aggregate by status
        if (!statusCounts[d.Status]) {
            statusCounts[d.Status] = 0;
        }
        statusCounts[d.Status] += d.count;

        // Aggregate by training
        if (!trainingCounts[d.Training]) {
            trainingCounts[d.Training] = 0;
        }
        trainingCounts[d.Training] += d.count;
    };
    
    // Prepare data for Google Charts
    let chartData = [['Category', 'Valid', 'Invalid', 'Assigned']],
        classes = {
            'BackgroundChecks': statusCounts,
            'Training': trainingCounts
        }
    maxValue = 0;
    for (const cl in classes) {
        chartData.push([cl, classes[cl]['Valid'] || 0, classes[cl]['Invalid'] || 0, classes[cl]['Assigned'] || 0])
        let sum = (classes[cl]['Valid'] || 0) + (classes[cl]['Invalid'] || 0) + (classes[cl]['Assigned'] || 0);
        if (sum > maxValue) { maxValue = sum; }
    }
    
    return [chartData, maxValue];
}

// Function to draw the chart
function drawChart(employee = 'all') {
    let [chartData, maxValue] = filterData(employee);


    let data = google.visualization.arrayToDataTable(chartData);

    let options = {
        chartArea: { width: '50%' },
        hAxis: {
            title: 'Total Count',
            viewWindow: {
                min: 0,
                max: maxValue
            }
        },
        vAxis: {
            title: 'Category',
        },
        isStacked: true,
        legend: { position: 'top', maxLines: 3 },
        colors: ['#49917b', '#ff0000', '#d95f02'] // Colors for status and training
    };

    let chart = new google.visualization.BarChart(document.getElementById('chart_div'));
    chart.draw(data, options);
}

// Event listener for employee filter
employeeFilter.addEventListener('change', function () {
    drawChart(this.value);
});

// Initial chart rendering (for all employees)
google.charts.setOnLoadCallback(() => drawChart('all'));


</script>

"""
