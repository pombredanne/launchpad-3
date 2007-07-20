/*
 * Adds the explicit branch type to the branch table.
 */

SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN branch_type INT;

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

ALTER TABLE Branch
ADD CONSTRAINT branch_type_url_consistent
CHECK ((branch_type = 2 AND url IS NOT NULL) OR url IS NULL);

-- Add some indexes we need to BranchSubscription
CREATE INDEX branchsubscription__person__idx ON BranchSubscription(person);
CREATE INDEX branchsubscription__branch__idx ON BranchSubscription(branch);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 31, 0);
