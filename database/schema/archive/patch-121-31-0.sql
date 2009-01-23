SET client_min_messages=ERROR;

ALTER TABLE BranchRevision DROP CONSTRAINT branchrevision_branch_fk;
ALTER TABLE BranchRevision ADD CONSTRAINT branchrevision__branch__fk
    FOREIGN KEY (branch) REFERENCES Branch ON DELETE CASCADE;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 31, 0);
