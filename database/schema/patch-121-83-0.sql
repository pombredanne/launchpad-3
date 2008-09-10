SET client_min_messages=ERROR;

ALTER TABLE BugWatch
    ADD COLUMN remote_lp_bug_id INTEGER;

ALTER TABLE BugTracker
    ADD COLUMN has_lp_plugin BOOLEAN;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 83, 0);
