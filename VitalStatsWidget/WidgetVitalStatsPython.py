import re
# You can report summary numbers for any status flag or saved search you have set up with this widget
# Example data is below, to use put the name you want to appear in the widget, followed by the status flag code or saved search name on each line
# You can also use multiple status flag codes in a line by separating them by a comma - this will show the number of people that have ALL of the specified flags
# You can link the number to any url as well with a third parameter

statusFlags = [
    ("Community Group", "F8"),
    ("Leaders", "F16"),
    ("Volunteers", "Volunteers", "/Query/f9449433-f972-46b0-95ab-ce142b5d54cb"),
    ("New Visitors", "F31"),
    ("Total", "F20"),
]

def Get():
    results = []
    template = Data.HTMLContent
    maxCnt = 1
    total = 0
    
    for item in statusFlags:
        flag = model.DynamicData()
        flag.name = item[0]
        flag.flag = item[1]
        if re.search('^F\d+(,F\d+)*$',item[1]) is None:
            flag.count = q.QueryCount(item[1])
        else:
            flag.count = q.StatusCount(item[1])
        maxCnt = max(maxCnt, flag.count)
        total += flag.count
        if len(item) > 2:
            flag.url = item[2]
        else:
            flag.url = '#'
        results.append(flag)
    
    Data.results = results
    Data.maxCnt = maxCnt
    Data.total = total
    print model.RenderTemplate(template)
Get()