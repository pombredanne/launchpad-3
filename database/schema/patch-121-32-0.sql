SET client_min_messages=ERROR;

-- Soyuz needs to ensure that files with the same name are not uploaded
-- to the distro with different contents. This requires an index on
-- filename to be done efficiently, as PG finds it cheaper to tablescan
-- the LFA table to filter the publishing tables rather than the other
-- way around.
CREATE INDEX libraryfilealias__filename__idx ON LibraryFileAlias(filename);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 32, 0);
