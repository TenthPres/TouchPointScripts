global model

sql = model.SqlContent('BudgetSummary').replace('@p1', '1')
d = model.SqlListDynamicData(sql)

def formatMoney(num):
    if num < 0:
        return "-${:-0,.0f}".format(num)
    else:
        return "${:-0,.0f}".format(num)

chart = ""

labelPositions = [[]]
def determineLine(x):
    margin = 80
    
    line = 1
    while True:
        c = False
        if len(labelPositions) <= line:
            labelPositions.append([])
        for lp in labelPositions[line]:
            if lp is None:
                continue
            
            if lp > x-margin and lp < x+margin:
                line += 1
                c = True
                continue
        if c:
            continue
        labelPositions[line].append(x)
        return line


def getMarkedLabel(x, y, label1, label2, textColor="#000", lineStyle="stroke:#999;stroke-width:1", extendTop=False):
    line = determineLine(x)
    yBase = y + 10  # top of bar
    y += line * 50 + 10  # top of the indicator (for line 1, bottom of the bar).
    
    yTop = yBase - (10 if extendTop else 0)
    r  = "<line x1=\"{0}\" y1=\"{2}\" x2=\"{0}\" y2=\"{3}\" style=\"{1}\" />".format(x, lineStyle, yTop, yBase+50)
    
    r += "<line x1=\"{0}\" y1=\"{2}\" x2=\"{0}\" y2=\"{3}\" style=\"{1}\" />".format(x, lineStyle, y, y+10)
    
    r += "<text x=\"{0}\" y=\"{1}\" fill=\"{2}\" style=\"text-anchor: middle\" font-family=\"Lato, sans-serif\">".format(x, y+25, textColor)
    r += "<tspan x=\"{0}\" dy=\"0\">{1}</tspan>".format(x, label1)
    r += "<tspan x=\"{0}\" dy=\"15\">{1}</tspan>".format(x, label2)
    r += "</text>"
    return r



# determine scaling
maxBudget = 1
for f in d:
    if f['Budget FY'] is not None and f['Budget FY'] > maxBudget:
        maxBudget = f['Budget FY']
        
yCum = 0

for f in d:
    givingPos = 100 + (500 * f["Giving YTD"]  / maxBudget)
    budgetPos = 100 + (500 * f["Budget YTD"]  / maxBudget) if f["Budget YTD"]  is not None else None
    prevPos =   100 + (500 * f["Giving PYTD"] / maxBudget) if f["Giving PYTD"] is not None else None
    barWidth =        (500 * f["Budget FY"] / maxBudget)   if f["Budget FY"]   is not None else None
    
    chart += "<!-- {} -->".format(f['Fund'])
    
    # fund label
    # chart += "<text x=\"{0}\" y=\"{1}\" fill=\"#000\">".format(3, yCum+35)
    # chart += "<tspan x=\"{0}\" dy=\"0\">{1}</tspan>".format(3, f['Fund'])
    # chart += "</text>"
    
    # base bar
    if barWidth is not None:
        chart += """<rect width="{0}" height="50" x="100" y="{1}" style="fill:#ccc;" />""".format(barWidth, yCum+10)
    
    # giving bar
    chart += """<rect width="{0}" height="50" x="100" y="{1}" style="fill:#49917b;" />""".format(givingPos-100, yCum+10)
    
    chart += getMarkedLabel(givingPos, yCum, "Giving YTD", formatMoney(f["Giving YTD"]))
    
    if f["Budget YTD"] is not None and f["Budget FY"] is not None and f["Budget YTD"] / f["Budget FY"] < 10.0/12:
        chart += getMarkedLabel(budgetPos, yCum, "Budget YTD", formatMoney(f["Budget YTD"]), "#000", "stroke:#000;stroke-width:3", True)
    
    if f["Budget FY"] is not None:
        chart += getMarkedLabel(barWidth+100, yCum, "Budget FY", formatMoney(f["Budget FY"]))
    
    chart += getMarkedLabel(prevPos, yCum, "Giving Last Year", formatMoney(f["Giving PYTD"]), "#999")
    
    height = len(labelPositions) * 50 + 10
    yCum += height
    labelPositions = [None]
    
    break

print("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg viewBox="0 0 700 {0}" xmlns="http://www.w3.org/2000/svg">
""".format(yCum))

print(chart)

print("</svg>")

#