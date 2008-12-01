SET client_min_messages=ERROR;

ALTER TABLE BranchRevision
    DROP CONSTRAINT branchrevision__branch__fk,
    DROP CONSTRAINT branchrevision__revision__fk;
ALTER TABLE BranchRevision
    ADD CONSTRAINT branchrevision__branch__fk
    FOREIGN KEY (branch) REFERENCES Branch
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT branchrevision__revision__fk
    FOREIGN KEY (revision) REFERENCES Revision
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 14, 0);
