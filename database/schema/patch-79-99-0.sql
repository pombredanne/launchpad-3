ALTER TABLE BugBranch DROP COLUMN revision_hint;

CREATE TABLE BugBranchRevision (
  id serial,
  bug integer CONSTRAINT bugbranchrevision_bug_fk REFERENCES Bug(id),
  branch integer CONSTRAINT bugbranchrevision_branch_fk REFERENCES Branch(id),
  revision integer CONSTRAINT bugbranchrevision_revision_fk REFERENCES Revision(id),
  status integer);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
