SET client_min_messages=ERROR;

-- Storing SHA256 for new library files.
ALTER TABLE LibraryFileContent ADD COLUMN sha256 char(64);

CREATE INDEX libraryfilecontent__sha256__idx
ON LibraryFileContent(sha256);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
