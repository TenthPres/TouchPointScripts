# This script adds the Atrium scripts to the MorningBatch and ScheduledTasks files, so they run automatically:
#   - AtriumSync (people and access levels), and a full AtriumScheduleSync, once a day in MorningBatch.
#   - A "near" AtriumScheduleSync (the next few hours only) from ScheduledTasks.  It runs at most about once an hour no
#     matter how often ScheduledTasks fires.
# Nothing changes in Atrium until "dryRun" is set to false in AtriumConfig.json.

global model, Data, q


def add_call(content_name, snippet, marker):
    content = model.PythonContent(content_name)
    if marker not in content:
        model.WriteContentPython(content_name, content + "\n\n" + snippet)


add_call("MorningBatch",
         '''# Atrium: daily sync
Data.AtriumScheduleMode = "full"
model.CallScript("AtriumSync")
model.CallScript("AtriumScheduleSync")''',
         'model.CallScript("AtriumSync")')

add_call("ScheduledTasks",
         '''# Atrium: near-term schedule refresh (self-throttled to about hourly)
Data.AtriumScheduleMode = "near"
model.CallScript("AtriumScheduleSync")''',
         'Data.AtriumScheduleMode = "near"')

print("REDIRECT=/PyScript/AtriumControl")  # This generally doesn't work, but we can dream.
