SET client_min_messages=ERROR;

ALTER TABLE LibraryFileContent ALTER COLUMN md5 SET NOT NULL;

CREATE INDEX libraryfilecontent__md5__idx ON LibraryFileContent(md5);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 61, 0);

