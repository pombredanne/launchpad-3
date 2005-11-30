SET client_min_messages=ERROR;

DROP INDEX idx_libraryfilecontent_sha1;
CREATE INDEX libraryfilecontent_sha1_filesize_idx
    ON LibraryFileContent(sha1, filesize);

-- Make last_accessed default to NOW.
ALTER TABLE LibraryFileAlias ALTER COLUMN last_accessed 
    SET DEFAULT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
-- One week ago to ensure all existing entries are garbage collectable
UPDATE LibraryFileAlias
    SET last_accessed = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        - '1 week'::interval
    WHERE last_accessed IS NULL;
ALTER TABLE LibraryFileAlias ALTER COLUMN last_accessed SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 03, 0);

