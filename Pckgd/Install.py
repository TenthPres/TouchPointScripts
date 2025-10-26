# This script adds Pckgd to the MorningBatch and ScheduledTask files, allowing automatic updates.

global model, Data, q

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("Pckgd")''' not in batchContent and '''model.CallScript('Pckgd')''' not in batchContent:
    batchContent = batchContent + '''\n\nData.pckgdCaller = "MorningBatch"\nmodel.CallScript("Pckgd")'''
    model.WriteContentPython("MorningBatch", batchContent)

batchContent = model.TextContent('ScheduledTasks')
if '''model.CallScript("Pckgd")''' not in batchContent and '''model.CallScript('Pckgd')''' not in batchContent:
    batchContent = batchContent + '''\n\nData.pckgdCaller = "ScheduledTasks"\nmodel.CallScript("Pckgd")'''
    model.WriteContentPython("ScheduledTasks", batchContent)

print("REDIRECT=/PyScript/Pckgd?c=installed")  # This generally doesn't work, but we can dream.