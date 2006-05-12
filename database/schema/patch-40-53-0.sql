SET client_min_messages=ERROR;

ALTER TABLE POSubmission ALTER COLUMN person SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 53, 0);
