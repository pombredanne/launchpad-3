SET client_min_messages=ERROR;

-- Backport constraint removal.
-- We can't rely on is_team in a constraint as it is only checked
-- on insert, and people can be switched to teams. Also, pg_dump and pg_restore
-- don't know is_team's dependancies so data required to give correct
-- results may not be loaded at the time the MailingList table is loaded.
ALTER TABLE mailinglist DROP CONSTRAINT is_team;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 42, 2);

