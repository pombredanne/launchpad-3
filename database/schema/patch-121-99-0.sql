SET client_min_messages=ERROR;

-- Refer to the Message table directly instead of through the Message-ID
ALTER TABLE BugWatch
    ADD COLUMN remote_lp_bug_id integer;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
