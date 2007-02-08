
-- Rename revisionnumber to branchrevision
ALTER TABLE revisionnumber RENAME TO branchrevision;

-- Allow NULLs in branchrevision.sequence
ALTER TABLE branchrevision ALTER COLUMN sequence DROP NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
