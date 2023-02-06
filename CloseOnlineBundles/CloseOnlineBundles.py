import clr
from System import DateTime

daysAgo = 2

sql = "SELECT TOP 100 ContributionDate FROM BundleHeader WHERE BundleHeaderTypeId = 4 AND BundleStatusId = 1 AND ContributionDate < DateAdd(d, -{}, getdate())".format(daysAgo)

for s in q.QuerySql(sql):
    bh = model.FindBundleHeader(s.ContributionDate, 'Online')
    if bh is not None:
        model.FinishBundle(bh)
        model.CloseBundle(bh)