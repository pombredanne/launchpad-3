SET client_min_messages=ERROR;

-- All pre-existing rows should have been updated off-line.
ALTER TABLE LibraryFileAlias ALTER COLUMN date_created SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 15, 0);
