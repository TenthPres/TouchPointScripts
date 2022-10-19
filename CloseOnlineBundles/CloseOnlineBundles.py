import clr
from System import DateTime

sql = "SELECT TOP 100 ContributionDate FROM BundleHeader WHERE BundleHeaderTypeId = 4 AND BundleStatusId = 1 AND ContributionDate < DateAdd(d, -4, getdate())"

for s in q.QuerySql(sql):
    bh = model.FindBundleHeader(s.ContributionDate)
    model.FinishBundle(bh)
    model.CloseBundle(bh)