
/*
  We are starting to make Sourcerer talk to the db, and these tweaks are required
  to make it work properly.

  Stub: this is good to go
*/

SET client_min_messages TO error;

-- need some tweaks to ManifestEntry
ALTER TABLE ManifestEntry ALTER COLUMN branch DROP NOT NULL;

ALTER TABLE Manifest ADD COLUMN uuid TEXT;

-- set the uuid's to be text versions of the id
UPDATE Manifest SET uuid = text(id);

ALTER TABLE Manifest ALTER COLUMN uuid SET NOT NULL;
ALTER TABLE Manifest 
    ADD CONSTRAINT "manifest_uuid_uniq"
            UNIQUE(uuid);

-- add id's to branchlabel and branchrelationship
ALTER TABLE BranchLabel ADD COLUMN id integer;
SET client_min_messages TO fatal;
CREATE SEQUENCE branchlabel_id_seq;
SET client_min_messages TO error;
ALTER TABLE BranchLabel ALTER COLUMN id SET NOT NULL;
ALTER TABLE BranchLabel ALTER COLUMN id
    SET DEFAULT nextval('branchlabel_id_seq');
ALTER TABLE BranchLabel ADD PRIMARY KEY (id);


ALTER TABLE BranchRelationship ADD COLUMN id integer;
SET client_min_messages TO fatal;
CREATE SEQUENCE branchrelationship_id_seq;
SET client_min_messages TO error;
ALTER TABLE BranchRelationship ALTER COLUMN id SET NOT NULL;
ALTER TABLE BranchRelationship ALTER COLUMN id
    SET DEFAULT nextval('branchrelationship_id_seq');
ALTER TABLE BranchRelationship DROP CONSTRAINT branchrelationship_pkey;
ALTER TABLE BranchRelationship ADD PRIMARY KEY (id);


-- change the SourcePackage table to make it more consistent
-- Not yet - too much breakage.
-- ALTER TABLE SourcePackage RENAME COLUMN distro TO distribution;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=15, patch=0;

