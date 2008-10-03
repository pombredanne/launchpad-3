SET client_min_messages=ERROR;

ALTER TABLE MessageApproval ADD COLUMN reason text;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 12, 0);

