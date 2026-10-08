-- ValidateRegistrationMigration.sql
--
-- Informal post-migration checklist for an Involvement converted from "Join Involvement" to
-- "Registration Form". Not a substitute for a human review -- several checks are informational
-- (they report a count so a person can judge whether it looks right) rather than a strict PASS/FAIL,
-- since a migration is allowed to legitimately change some of these numbers (e.g. splitting one
-- person's repeat registrations into separate submissions is the point, not a bug).
--
-- Usage: set @OrganizationId below and run the whole script in SSMS (or sqlcmd) against the
-- Involvement's TouchPoint database after running the migration.

DECLARE @OrganizationId INT = 0; -- <-- set this

IF OBJECT_ID('tempdb..#Results') IS NOT NULL DROP TABLE #Results;
CREATE TABLE #Results (
    Ord INT IDENTITY(1,1),
    Check_ NVARCHAR(100),
    Result NVARCHAR(10),
    Detail NVARCHAR(400)
);

-- 1. The involvement exists and is now Registration Form (RegistrationTypeId = 26)
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'RegistrationType',
       CASE WHEN RegistrationTypeId = 26 THEN 'PASS' ELSE 'FAIL' END,
       'RegistrationTypeId = ' + CAST(ISNULL(RegistrationTypeId, -1) AS NVARCHAR(10)) + ' (26 = Registration Form)'
FROM Organizations
WHERE OrganizationId = @OrganizationId;

IF @@ROWCOUNT = 0
    INSERT INTO #Results (Check_, Result, Detail) VALUES ('RegistrationType', 'FAIL', 'No such OrganizationId');

-- 2. At least one RegQuestion exists, including a PersonInfo question (QuestionTypeId = 5)
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'RegQuestions exist',
       CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' question(s)'
FROM RegQuestion
WHERE OrganizationId = @OrganizationId;

INSERT INTO #Results (Check_, Result, Detail)
SELECT 'PersonInfo question present',
       CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' PersonInfo question(s)'
FROM RegQuestion
WHERE OrganizationId = @OrganizationId AND QuestionTypeId = 5;

-- 3. Roster size vs. migrated registrants, for eyeballing -- not necessarily equal, since one
--    roster member can now correspond to several distinct Registrations.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'Roster vs RegPeople counts',
       'INFO',
       (SELECT CAST(COUNT(*) AS NVARCHAR(10)) FROM OrganizationMembers WHERE OrganizationId = @OrganizationId)
           + ' roster member(s), '
           + CAST((SELECT COUNT(DISTINCT rp.PeopleId)
                   FROM RegPeople rp
                   JOIN Registration r ON r.RegistrationId = rp.RegistrationId
                   WHERE r.OrganizationId = @OrganizationId) AS NVARCHAR(10))
           + ' distinct migrated person(s), '
           + CAST((SELECT COUNT(*)
                   FROM RegPeople rp
                   JOIN Registration r ON r.RegistrationId = rp.RegistrationId
                   WHERE r.OrganizationId = @OrganizationId) AS NVARCHAR(10))
           + ' total Registration(s)';

-- 4. No empty Registrations (a submission record with nobody attached to it)
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'No empty Registrations',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' Registration(s) with no RegPeople'
FROM Registration r
WHERE r.OrganizationId = @OrganizationId
  AND NOT EXISTS (SELECT 1 FROM RegPeople rp WHERE rp.RegistrationId = r.RegistrationId);

-- 5. No cross-linked RegAnswers (answer's question or person belongs to a different involvement --
--    a sign of a copy/paste id mistake during migration)
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'No cross-org RegAnswers',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' RegAnswer(s) referencing a different involvement'
FROM RegAnswer a
JOIN RegPeople rp ON rp.RegPeopleId = a.RegPeopleId
JOIN Registration r ON r.RegistrationId = rp.RegistrationId
JOIN RegQuestion q ON q.RegQuestionId = a.RegQuestionId
WHERE r.OrganizationId = @OrganizationId
  AND q.OrganizationId <> @OrganizationId;

-- 6. Migrated RegPeople whose PeopleId has no matching roster row for this involvement -- worth a
--    look (could be intentional, e.g. a family member added during registration, but for a straight
--    historical migration this is usually unexpected)
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'RegPeople without a roster row',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'INFO' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' RegPeople row(s) with no matching OrganizationMembers row'
FROM RegPeople rp
JOIN Registration r ON r.RegistrationId = rp.RegistrationId
WHERE r.OrganizationId = @OrganizationId
  AND rp.PeopleId IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM OrganizationMembers om
      WHERE om.OrganizationId = @OrganizationId AND om.PeopleId = rp.PeopleId
  );

-- 7. Dollar total sanity check: money already attributed to this involvement's people (via the
--    long-standing TransactionPeople table) vs. money now linked to a Registration. These are not
--    required to match exactly -- a transaction can predate TransactionPeople tracking, or a
--    person's payment might not yet be linked to a specific submission -- but a large gap is worth
--    investigating.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'Linked vs. attributed dollars',
       CASE WHEN ABS(ISNULL(linked.Total, 0) - ISNULL(attributed.Total, 0)) < 0.01 THEN 'PASS' ELSE 'INFO' END,
       'Linked to a Registration: ' + CAST(ISNULL(linked.Total, 0) AS NVARCHAR(20))
           + '; attributed to this involvement via TransactionPeople: ' + CAST(ISNULL(attributed.Total, 0) AS NVARCHAR(20))
FROM (
    SELECT SUM(t.amt) AS Total
    FROM [Transaction] t
    JOIN Registration r ON r.RegistrationId = t.RegistrationId
    WHERE r.OrganizationId = @OrganizationId
) linked
CROSS JOIN (
    SELECT SUM(tp.Amt) AS Total
    FROM TransactionPeople tp
    WHERE tp.OrgId = @OrganizationId
) attributed;

-- 8. Transactions attributed to this involvement that still aren't linked to any Registration --
--    candidates for LinkTransactionToRegistration
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'Unlinked transactions remaining',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'INFO' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' transaction(s) attributed to this involvement with no RegistrationId'
FROM TransactionPeople tp
JOIN [Transaction] t ON t.Id = tp.Id
WHERE tp.OrgId = @OrganizationId
  AND t.RegistrationId IS NULL;

-- 9. People with more than one Registration for this involvement -- expected and fine; this is the
--    ambiguity the migration is meant to resolve, not a defect. Reported for visibility only.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'People with multiple Registrations',
       'INFO',
       CAST(COUNT(*) AS NVARCHAR(10)) + ' distinct person/count-of-registrations pair(s) with more than one submission'
FROM (
    SELECT rp.PeopleId
    FROM RegPeople rp
    JOIN Registration r ON r.RegistrationId = rp.RegistrationId
    WHERE r.OrganizationId = @OrganizationId AND rp.PeopleId IS NOT NULL
    GROUP BY rp.PeopleId
    HAVING COUNT(*) > 1
) multi;

-- 10. RegQuestion.Options is well-formed JSON where present -- the migration script builds this from
--     Python dicts/lists via .ToJSON(), which was never independently verified end-to-end; a
--     malformed value here would break the Registration Form builder/renderer for that question.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'RegQuestion Options is valid JSON',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' question(s) with malformed Options JSON'
FROM RegQuestion
WHERE OrganizationId = @OrganizationId
  AND Options IS NOT NULL
  AND ISJSON(Options) = 0;

-- 11. No duplicate RegAnswers for the same RegPeople/RegQuestion pair. model.AddRegAnswer refuses a
--     duplicate, but this checks the data itself rather than trusting that guard was exercised.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'No duplicate RegAnswers',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' RegPeople/RegQuestion pair(s) with more than one RegAnswer'
FROM (
    SELECT a.RegPeopleId, a.RegQuestionId
    FROM RegAnswer a
    JOIN RegPeople rp ON rp.RegPeopleId = a.RegPeopleId
    JOIN Registration r ON r.RegistrationId = rp.RegistrationId
    WHERE r.OrganizationId = @OrganizationId
    GROUP BY a.RegPeopleId, a.RegQuestionId
    HAVING COUNT(*) > 1
) dupes;

-- 12. RegAnswer.AnswerValue is valid JSON. The Registration Form UI JSON.parses it and the server reads
--     it with FromJson (which yields nothing for a bare string), so a plain-text answer is unreadable.
INSERT INTO #Results (Check_, Result, Detail)
SELECT 'RegAnswer AnswerValue is valid JSON',
       CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       CAST(COUNT(*) AS NVARCHAR(10)) + ' answer(s) whose AnswerValue is not valid JSON'
FROM RegAnswer a
JOIN RegPeople rp ON rp.RegPeopleId = a.RegPeopleId
JOIN Registration r ON r.RegistrationId = rp.RegistrationId
WHERE r.OrganizationId = @OrganizationId
  AND a.AnswerValue IS NOT NULL
  AND ISJSON(a.AnswerValue) = 0;

SELECT Check_, Result, Detail FROM #Results ORDER BY Ord;

DROP TABLE #Results;
