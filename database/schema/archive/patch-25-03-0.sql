set client_min_messages=ERROR;

ALTER TABLE POFile ADD COLUMN latestsubmission integer;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 03, 0);
