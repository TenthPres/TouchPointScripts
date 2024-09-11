global model

sql = model.SqlContent('BudgetSummary').replace('@p1', '0')
d = model.SqlListDynamicData(sql)

def formatMoney(num):
    if num < 0:
        return "-${:-0,.0f}".format(num)
    else:
        return "${:-0,.0f}".format(num)


print("""
<table>
<tr>
    <th style="padding:.2em;">2024</th>
    <th style="padding:.2em; text-align:center;">{0}</th>
</tr>
<tr>
    <th style="padding:.2em;">Giving Budget</th>
    <td style="padding:.2em; text-align:right">{1}</td>
</tr>
<tr>
    <td style="padding:.2em;"></td>
    <td style="padding:.2em;"></td>
</tr>
<tr style="border-top:2px solid #000">
    <td style="padding:.2em;"></td>
    <td style="padding:.2em;"></td>
</tr>
<tr>
    <th style="padding:.2em;">YTD Budget</th>
    <td style="padding:.2em; text-align:right">{2}</td>
</tr>
<tr>
    <th style="padding:.2em;">YTD Giving</th>
    <td style="padding:.2em; text-align:right">{3}</td>
</tr>
<tr style="border-top:1px solid #000">
    <th style="padding:.2em;">YTD Difference</th>
    <td style="padding:.2em; text-align:right">{4}</td>
</tr>
</table>""".format(
    d[0]["Fund"], 
    formatMoney(d[0]["Budget FY"]),
    formatMoney(d[0]["Budget YTD"]),
    formatMoney(d[0]["Giving YTD"]),
    formatMoney(d[0]["YTD Difference"]),
))

print("<p>{0}: {1}</p>".format(d[1]["Fund"], formatMoney(d[1]["Giving YTD"])))

print("<p>All data current through {0}.</p>".format(d[0]["As Of"].ToString('dddd, MMMM d, yyyy')))