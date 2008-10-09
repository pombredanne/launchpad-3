SET client_min_messages=ERROR;

DROP INDEX archivedependency__unique__temp;

ALTER TABLE ArchiveDependency
    DROP CONSTRAINT archivedependency_unique,
    ADD CONSTRAINT archivedependency__unique UNIQUE (archive, dependency),
    ALTER COLUMN pocket SET NOT NULL;



INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

