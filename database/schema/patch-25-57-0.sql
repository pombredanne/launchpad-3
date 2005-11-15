SET client_min_messages=ERROR;

DROP INDEX idx_libraryfilecontent_sha1;
CREATE INDEX libraryfilecontent_sha1_filesize_idx
    ON LibraryFileContent(sha1, filesize);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 57, 0);

