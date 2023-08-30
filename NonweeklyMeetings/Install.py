# This script adds NonWeekly Meetings to the MorningBatch so meetings are created automatically.
# Then, execute the first round of creation.

batchContent = model.PythonContent('MorningBatch')
if '''model.CallScript("NonweeklyMeetings")''' not in batchContent and '''model.CallScript('NonweeklyMeetings')''' not in batchContent:
    batchContent = batchContent + '''\n\nmodel.CallScript("NonweeklyMeetings")'''
    model.WriteContentPython("MorningBatch", batchContent)

standardValues = model.TextContent('StandardExtraValues2')
if '''Name="Meeting Frequency" ''' not in standardValues:
    if '''View Table="Organization" Location="Standard"''' in standardValues:
        standardValueXml = '''    <Value Name="Meeting Frequency" Type="Bits" VisibilityRoles="Access">
              <Code>Frequency:Every Other</Code>
              <Code>Frequency:First</Code>
              <Code>Frequency:Second</Code>
              <Code>Frequency:Third</Code>
              <Code>Frequency:Fourth</Code>
              <Code>Frequency:Fifth</Code>
            </Value>'''
        sectionStart = '''<View Table="Organization" Location="Standard">'''
        standardValues = standardValues.replace(sectionStart, sectionStart + "\n" + standardValueXml, 1)
    else:
        standardValueXml = '''  <View Table="Organization" Location="Standard">\n    <Value Name="Meeting Frequency" Type="Bits" VisibilityRoles="Access">
              <Code>Frequency:Every Other</Code>
              <Code>Frequency:First</Code>
              <Code>Frequency:Second</Code>
              <Code>Frequency:Third</Code>
              <Code>Frequency:Fourth</Code>
              <Code>Frequency:Fifth</Code>
            </Value>\n  </View>'''
        sectionStart = '''<Views>'''
        standardValues = standardValues.replace(sectionStart, sectionStart + "\n" + standardValueXml, 1)
    model.WriteContentText("StandardExtraValues2", standardValues)

model.CallScript("NonweeklyMeetings")
