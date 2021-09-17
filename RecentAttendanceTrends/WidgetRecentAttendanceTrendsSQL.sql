select MaxCount, d.ProgId ProgramId, dbo.SundayForDate(m.MeetingDate) ss, 
    datediff(hour, dbo.SundayForDate(m.MeetingDate), m.MeetingDate) hh
    into #meetingdata
from dbo.Meetings m
join dbo.Organizations o on o.OrganizationId = m.OrganizationId
join dbo.DivOrg dd on dd.orgid = o.OrganizationId
join dbo.Division d on d.Id = dd.DivId
where d.ProgId in (@progs)
and MaxCount > 0;
with data as (
	select MaxCount, ProgramId, ss, hh 
	from #meetingdata
	where ss >= '@begindate'
	and ss <= SYSDATETIME()
)
select CONVERT(varchar, ss, 111) [Sunday], @rowcounts
from data dd
group by dd.ss
drop table #meetingdata