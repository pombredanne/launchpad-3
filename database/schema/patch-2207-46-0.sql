SET client_min_messages=ERROR;

DROP VIEW RevisionNumber;

ALTER TABLE BranchRevision ALTER COLUMN id TYPE bigint;

CREATE VIEW RevisionNumber AS
SELECT
    branchrevision.id, branchrevision.sequence,
    branchrevision.branch, branchrevision.revision
FROM branchrevision;


INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 46, 0);
