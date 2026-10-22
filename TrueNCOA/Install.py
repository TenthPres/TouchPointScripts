# This script adds CheckNCOAStatus to the Morning Batch, so submitted files get checked -- and re-checked for
# TrueNCOA's free NCOA updates -- automatically every day, without anyone needing to remember to run it by hand.
#
# Run this once, after CheckNCOAStatus.py (and SubmitToNCOA.py) have already been created as their own Special
# Content Python Script documents with those exact names.

global model, Data, q

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("CheckNCOAStatus")''' not in batchContent and '''model.CallScript('CheckNCOAStatus')''' not in batchContent:
    batchContent = batchContent + '''\n\nmodel.CallScript("CheckNCOAStatus")'''
    model.WriteContentPython("MorningBatch", batchContent)

print "<p>CheckNCOAStatus will now run automatically as part of the Morning Batch.</p>"

model.CallScript("CheckNCOAStatus")
