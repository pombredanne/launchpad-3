SET client_min_messages=ERROR;

-- Looks like a hang over from when dropping the tables didn't
-- drop the associated series sequence.
DROP SEQUENCE branchlabel_id_seq;

-- Not used any more (if ever).
DROP TABLE ArchConfigEntry;
DROP TABLE ArchConfig;
DROP TABLE BranchMessage;
DROP TABLE BranchRelationship;
DROP TABLE ProductBranchRelationship;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 38, 0);
