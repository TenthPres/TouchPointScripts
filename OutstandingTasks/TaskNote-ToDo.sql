SELECT t.PeopleId, COUNT(*)
FROM (SELECT *, tn.OwnerId AS PeopleId
      FROM TaskNote tn
      WHERE (tn.StatusId = 4 OR -- Declined
             ((tn.StatusId = 2 OR tn.StatusId = 3) AND tn.AssigneeId IS NULL))
        AND tn.Instructions NOT LIKE 'New Person Data Entry%'
      UNION
      SELECT *, ta.AssigneeId AS PeopleId
      FROM TaskNote ta
      WHERE (ta.StatusId = 2 OR ta.StatusId = 3)
        AND ta.AssigneeId IS NOT NULL
        AND ta.Instructions NOT LIKE 'New Person Data Entry%') t
GROUP BY t.peopleId