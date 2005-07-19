set client_min_messages=ERROR;

ALTER TABLE POTemplate DROP COLUMN rawfile_;
ALTER TABLE POFile DROP COLUMN rawfile_;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 12, 0);

