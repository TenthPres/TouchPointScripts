# This script adds Mapify to the MorningBatch to keep lat/lng populated and updated.  It then runs an initial batch.

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("Mapify")''' not in batchContent and '''model.CallScript('Mapify')''' not in batchContent:
    batchContent = batchContent + '''\n\nmodel.CallScript("Mapify")'''
    model.WriteContentPython("MorningBatch", batchContent)

# TODO add to report menu

model.CallScript("Mapify")
