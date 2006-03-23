
SET client_min_messages=ERROR;

ALTER TABLE LibraryFileContent ADD COLUMN md5 character(32);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 35, 0);
