
-- Rename revisionnumber to branchrevision.
ALTER TABLE revisionnumber RENAME TO branchrevision;

-- Rename constraints.
ALTER TABLE branchrevision
    DROP CONSTRAINT revisionnumber_branch_fk;

ALTER TABLE branchrevision
    DROP CONSTRAINT revisionnumber_revision_fk;

ALTER TABLE branchrevision
    ADD CONSTRAINT branchrevision_branch_fk FOREIGN KEY (branch) REFERENCES branch(id);

ALTER TABLE branchrevision
    ADD CONSTRAINT branchrevision_revision_fk FOREIGN KEY (revision) REFERENCES revision(id);

-- Rename indexes.
ALTER INDEX revisionnumber_pkey
    RENAME TO branchrevision_pkey;

ALTER INDEX revisionnumber_branch_id_unique
    RENAME TO branchrevision_branch_id_unique;

ALTER INDEX revisionnumber_branch_sequence_unique
    RENAME TO branchrevision_branch_sequence_unique;

ALTER INDEX revisionnumber_revision_branch_unique
    RENAME TO branchrevision_revision_branch_unique;

-- Rename sequences.
ALTER TABLE revisionnumber_id_seq
    RENAME TO branchrevision_id_seq;

-- Allow NULLs in branchrevision.sequence.
ALTER TABLE branchrevision ALTER COLUMN sequence DROP NOT NULL;


/* Create a VIEW and some rules as code has yet to be updated to use the
   new table name */
CREATE VIEW RevisionNumber AS SELECT * FROM BranchRevision;
CREATE RULE insert_rule AS ON INSERT TO RevisionNumber DO INSTEAD
    INSERT INTO BranchRevision VALUES (
        NEW.id, NEW.sequence, NEW.branch, NEW.revision
    );
CREATE RULE update_rule AS ON UPDATE TO RevisionNumber DO INSTEAD
    UPDATE BranchRevision
    SET id=New.id, sequence=NEW.sequence,
        branch=NEW.branch, revision=NEW.revision
    WHERE id=OLD.id;
CREATE RULE delete_rule AS ON DELETE TO RevisionNumber DO INSTEAD
    DELETE FROM BranchRevision WHERE id=OLD.id;


INSERT INTO LaunchpadDatabaseRevision VALUES (79, 05, 0);
