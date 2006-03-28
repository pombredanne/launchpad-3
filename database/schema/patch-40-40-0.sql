SET client_min_messages=ERROR;

ALTER TABLE BugBranch RENAME COLUMN fixed_in_revision TO revision_hint;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 40, 0);