SET client_min_messages TO error;

/* Add owner to bug assignment tables */

ALTER TABLE ProductBugAssignment ADD COLUMN owner integer;
ALTER TABLE ProductBugAssignment ADD CONSTRAINT productbugassignment_owner_fk
    FOREIGN KEY (owner) REFERENCES Person(id);

ALTER TABLE SourcePackageBugAssignment ADD COLUMN owner integer;
ALTER TABLE SourcePackageBugAssignment
    ADD CONSTRAINT sourcepackagebugassignment_owner_fk
    FOREIGN KEY (owner) REFERENCES Person(id);

UPDATE ProductBugAssignment SET owner = Bug.owner
    FROM Bug WHERE ProductBugAssignment.bug = Bug.id;

UPDATE SourcePackageBugAssignment SET owner = Bug.owner
    FROM Bug WHERE SourcepackageBugAssignment.bug = Bug.id;

ALTER TABLE ProductBugAssignment ALTER COLUMN owner SET NOT NULL;
ALTER TABLE SourcepackageBugAssignment ALTER COLUMN owner SET NOT NULL;

/* And we want indexes since we use owner to join */
CREATE INDEX productbugassignment_owner_idx ON ProductBugAssignment(owner);
CREATE INDEX sourcepackagebugassignment_owner_idx 
    ON SourcePackageBugAssignment(owner);

UPDATE LaunchpadDatabaseRevision SET major=4, minor=7, patch=0;

/* Add version constraints */
ALTER TABLE BinaryPackage
    ADD CONSTRAINT valid_version CHECK (valid_version(version));
ALTER TABLE DistroRelease
    ADD CONSTRAINT valid_version CHECK (valid_version(version));
ALTER TABLE ProductRelease
    ADD CONSTRAINT valid_version CHECK (valid_version(version));
ALTER TABLE SourcePackageRelease
    ADD CONSTRAINT valid_version CHECK (valid_version(version));
