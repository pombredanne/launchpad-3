SET client_min_messages=ERROR;

-- Add pocket and component columns to the ArchiveDependency table.
-- We will update the records and add the NOT NULL constraint in the
-- next cycle, when the code to fill those values will be implemented.

ALTER TABLE ArchiveDependency
    ADD COLUMN pocket INT,
    ADD COLUMN component INT REFERENCES Component(id);


-- Update the unique constraint to also consider the new columns.
-- Since they will be NULL for the during the next cycle, it's basically
-- the same than it was before, but it will be ready to cope with the
-- columns values if we decided to cherrypick the code.

ALTER TABLE ArchiveDependency DROP CONSTRAINT archivedependency_unique;
ALTER TABLE ArchiveDependency
    ADD CONSTRAINT archivedependency_unique UNIQUE (
        archive, dependency, pocket, component);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
