
SET client_min_messages=ERROR;

ALTER TABLE LibraryFileContent ADD COLUMN md5 character(32);

-- XXX: need real revision number
INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);
