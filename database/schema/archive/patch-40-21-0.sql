SET client_min_messages=ERROR;

ALTER TABLE Build DROP COLUMN changes;
ALTER TABLE Build DROP COLUMN gpgsigningkey;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 21, 0);

