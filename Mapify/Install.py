# This script adds Mapify to the MorningBatch to keep lat/lng populated and updated.  It then adds it to the custom
# report menu and runs an initial batch of geocoding.

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("Mapify")''' not in batchContent and '''model.CallScript('Mapify')''' not in batchContent:
    batchContent = batchContent + '''\n\nmodel.CallScript("Mapify")'''
    model.WriteContentPython("MorningBatch", batchContent)

reportMenu = model.TextContent('CustomReports')
if '''name="Mapify" type="PyScript"''' not in reportMenu:
    MapifyReportLine = '''  <Report name="Mapify" type="PyScript" role="Access" />\n'''
    reportMenu = reportMenu.replace("</CustomReports", MapifyReportLine + "</CustomReports", 1)
    model.WriteContentText("CustomReports", reportMenu)

model.CallScript("Mapify")
