SET client_min_messages=ERROR;

ALTER TABLE buildqueue ADD COLUMN manual boolean;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);
