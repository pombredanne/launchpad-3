SET client_min_messages=ERROR;

-- The number of days before superseded or deleted binary files are expired in
-- the librarian, or zero for never.
ALTER TABLE Archive
    ADD COLUMN removed_binary_retention_days integer;

-- The number of versions of a package to keep published before older
-- versions are superseded. Note this isn't a counter, so we don't use
-- the _count suffix used elsewhere.
ALTER TABLE Archive
    ADD COLUMN num_old_versions_published integer;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 30, 0);
