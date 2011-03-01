SET client_min_messages=ERROR;

DROP VIEW RevisionNumber;

ALTER TABLE BranchRevision DROP COLUMN id;
ALTER TABLE BranchRevision
    ADD CONSTRAINT branchrevision_pkey
        PRIMARY KEY (branch, revision);
ALTER TABLE BranchRevision
    DROP CONSTRAINT revision__branch__revision__key,
    DROP CONSTRAINT revision__revision__branch__key,
    DROP CONSTRAINT revisionnumber_branch_sequence_unique;
CREATE UNIQUE INDEX branchrevision__branch__sequence__key
    ON BranchRevision (branch, sequence) WHERE sequence IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 49, 0);
