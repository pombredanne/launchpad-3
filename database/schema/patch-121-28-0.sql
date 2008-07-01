SET client_min_messages=ERROR;

-- Add pocket and component columns to the ArchiveDependency table.
-- We will update the records and add the NOT NULL constraint in the
-- next cycle, when the code to fill those values will be implemented.

ALTER TABLE ArchiveDependency
    ADD COLUMN pocket INT,
    ADD COLUMN component INT REFERENCES Component(id);


-- Update the unique constraint to also consider the new columns.
-- Since they will be NULL for the during the next cycle, we also need
-- a temporary partial index to enforce integrity until the NOT NULL
-- constraints can be added.

ALTER TABLE ArchiveDependency DROP CONSTRAINT archivedependency_unique;
ALTER TABLE ArchiveDependency
    ADD CONSTRAINT archivedependency_unique UNIQUE (
        archive, dependency, pocket, component);
CREATE UNIQUE INDEX archivedependency__unique__temp
    ON ArchiveDependency(archive, dependency)
    WHERE (pocket IS NULL OR component IS NULL);

CREATE INDEX archivedependency__component__idx
    ON ArchiveDependency(component);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 28, 0);
