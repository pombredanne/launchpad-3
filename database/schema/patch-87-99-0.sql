/*
 * Adds the explicit branch type to the branch table.
 */

SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN type INT;

UPDATE Branch
SET branch_type = 3 -- IMPORTED
WHERE owner IN (
   SELECT id FROM Person
   WHERE name = 'vcs-imports');

UPDATE Branch
SET branch_type = 2 -- MIRRORED
WHERE url IS NOT NULL
  AND branch_type IS NULL;

UPDATE Branch
SET branch_type = 1 -- HOSTED
WHERE branch_type IS NULL;

ALTER TABLE Branch ALTER branch_type SET DEFAULT 0;
ALTER TABLE Branch ALTER branch_type SET NOT NULL;

-- To be moved to comments.sql
COMMENT ON COLUMN Branch.branch_type IS 'Branches are currently one of HOSTED (1), MIRRORED (2), or IMPORTED (3).';


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);

