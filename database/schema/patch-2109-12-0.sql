-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BranchRevision
    DROP CONSTRAINT branchrevision__branch__fk,
    DROP CONSTRAINT branchrevision_revision_fk;
ALTER TABLE BranchRevision
    ADD CONSTRAINT branchrevision__branch__fk
    FOREIGN KEY (branch) REFERENCES Branch DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT branchrevision__revision__fk
    FOREIGN KEY (revision) REFERENCES Revision DEFERRABLE INITIALLY DEFERRED;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 12, 0);
