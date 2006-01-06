SET client_min_messages=ERROR;

-- Add last_accessed timestamp to LibraryFileAlias
ALTER TABLE LibraryFileAlias
    ADD COLUMN last_accessed timestamp without time zone;
ALTER TABLE LibraryFileAlias ALTER COLUMN last_accessed SET DEFAULT NULL;

-- Add deleted flag to LibraryFileContent to flag files that have been
-- removed from the Librian
ALTER TABLE LibraryFileContent ADD COLUMN deleted boolean;
UPDATE LibraryFileContent SET deleted = false;
ALTER TABLE LibraryFileContent ALTER COLUMN deleted SET NOT NULL;
ALTER TABLE LibraryFileContent ALTER COLUMN deleted SET DEFAULT false;


-- XXX: sampledata to move to sampledata -- StuartBishop 20050906
-- INSERT INTO LibraryFileContent (id, filesize, sha1, deleted) VALUES (
--    36, 3, sha1('foo'), true
--    );
--INSERT INTO LibraryFileAlias (id, content, filename, mimetype) VALUES (
--    36, 36, 'foo.txt', 'text/plain'
--    );

/*
INSERT INTO LibraryFileContent (id, filesize, sha1) VALUES (
    36, 3, sha1('bar')
    );
INSERT INTO LibraryFileAlias (id, content, filename, mimetype) VALUES (
    36, 'foo.txt', 'text/plain'
    );
INSERT INTO LibraryFileAlias (id, content, filename, mimetype) VALUES (
    37, 'foo.txt', 'text/plain'
    );
*/
    


INSERT INTO LaunchpadDatabaseRevision VALUES (25, 22, 0);

