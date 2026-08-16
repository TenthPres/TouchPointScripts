# This script adds SchedulerSyncer to the MorningBatch and ScheduledTask files, so processing happens automatically.

global model, Data, q

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("SchedulerSyncer")''' not in batchContent and '''model.CallScript('SchedulerSyncer')''' not in batchContent:
    batchContent = batchContent + '''\n\nData.SchedulerSyncerCaller = "MorningBatch"\nmodel.CallScript("SchedulerSyncer")'''
    model.WriteContentPython("MorningBatch", batchContent)

batchContent = model.PythonContent('ScheduledTasks')
if '''model.CallScript("SchedulerSyncer")''' not in batchContent and '''model.CallScript('SchedulerSyncer')''' not in batchContent:
    batchContent = batchContent + '''\n\nData.SchedulerSyncerCaller = "ScheduledTasks"\nmodel.CallScript("SchedulerSyncer")'''
    model.WriteContentPython("ScheduledTasks", batchContent)

print("REDIRECT=/PyScript/SchedulerSyncer?a=installed")  # This generally doesn't work, but we can dream.