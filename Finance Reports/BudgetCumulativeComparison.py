import json

global model

sql = model.SqlContent('BudgetCumulativeGivingYoY')

# Initialize data structure to store percentages by year and week
weeks = range(1, 54)  # Assuming there are 52 weeks
years = []
d = []  # Will store data for each year, where each entry is a list of 52 weeks

# Retrieve the data from the database
dbd = model.SqlListDynamicData(sql)

# Process the data and dynamically build the year-week-percentage matrix
year_index_map = {}
for row in dbd:
    # If it's a new year, initialize a new entry in the data matrix
    if row.Year not in year_index_map:
        year_index_map[row.Year] = len(years)  # Assign a new column index for this year
        years.append(row.Year)  # Track the year
        d.append([None] * 53)  # Initialize 52 weeks with 'None' for this year

    # Get the column index for the current year
    year_col = year_index_map[row.Year]

    # Assign the percentage value for the corresponding week (row.Week - 1)
    if 1 <= row.Week <= 53:  # Ensure the week is within a valid range (1-52)
        d[year_col][row.Week - 1] = row.Percentage
    if row.Week > 53:
        d[year_col][52] = row.Percentage

# Generate Google Chart script
print """<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>"""
print "<script>"
print "google.charts.load('current', {'packages':['corechart']});"
print "google.charts.setOnLoadCallback(drawChart);"
print "function drawChart() {"
print "var data = new google.visualization.DataTable();"

# Define columns: the first column is for the weeks, followed by one column per year
print "data.addColumn('number', 'Week');"
for y in years:
    print "data.addColumn('number', '{}');".format(y)

# Add rows for each week (1 to 52), with percentages for each year
print "data.addRows("
rows = []
for week in range(53):  # Loop through 52 weeks
    row_data = [week + 1]  # Start with the week number
    for year_index in range(len(years)):
        # Ensure the data is JSON serializable: float or None
        value = d[year_index][week] if d[year_index][week] is not None else None
        row_data.append(float(value/100) if value is not None else None)  # Force float if it's not None
    rows.append(row_data)

# Use json.dumps to correctly serialize Python None as JavaScript null
print json.dumps(rows)
print ");"

# Generate colors and widths
colors = ["'#ccc'"] * (len(years) - 2) + ["'#000'", "'#00f'"]
widths = ['1'] * (len(years) - 2) + ['5', '5']


# Set chart options
print """
var options = {
  title: 'Cumulative Giving as Percentage of Budget',
  curveType: 'function',
  hAxis: {title: 'Week'},
  vAxis: {
    title: 'Percentage of Budget',
    viewWindow: {min: 0, max: 1.09},
    format: 'percent'
  },
  series: {"""
for i in range(len(years)-2):
    print str(i) + ": { lineWidth: 1 },"
print """},
  legend: 'none',  // Hide legend
  colors: [""" + ", ".join(colors) + """],
  lineWidth: 5
};
"""

# Draw the chart
print """
var chart = new google.visualization.LineChart(document.getElementById('curve_chart'));
chart.draw(data, options);
}
</script>

<div id="curve_chart" style="width: 100%; height: 10in"></div>
"""