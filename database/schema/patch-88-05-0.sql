SET client_min_messages=ERROR;

-- The BranchSubscription is missing a unique constraint.
-- A person should never be subscribed to a single branch more than once.

ALTER TABLE BranchSubscription
    ADD CONSTRAINT branchsubscription__person__branch__key
    UNIQUE(person, branch);

-- No longer needed
DROP INDEX branchsubscription__person__idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 05, 0);

