SET client_min_messages=ERROR;

ALTER TABLE personlocation ALTER COLUMN time_zone DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 79, 0);
