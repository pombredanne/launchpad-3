ALTER TABLE BugBranch DROP COLUMN revision_hint;

CREATE TABLE BugBranchRevision (
  id serial,
  bug integer NOT NULL CONSTRAINT bugbranchrevision_bug_fk REFERENCES Bug(id),
  branch integer CONSTRAINT bugbranchrevision_branch_fk REFERENCES Branch(id),
  revision integer NOT NULL CONSTRAINT bugbranchrevision_revision_fk REFERENCES Revision(id),
  status integer);

CREATE TABLE RevisionProperty (
  id serial,
  revision integer CONSTRAINT revisionproperty_fk REFERENCES Revision(id),
  name text NOT NULL,
  value text NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);
