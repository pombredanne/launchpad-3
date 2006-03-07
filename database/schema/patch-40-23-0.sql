SET client_min_messages=ERROR;

ALTER TABLE Build ADD COLUMN dependencies text;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 23, 0);
