
/*
  We need to give the SpokenIn table a primary key id. What makes this fun
  is that there is already data in there. Hence the UPDATE to set each row
  to have a unique ID.

*/

ALTER TABLE SpokenIn ADD COLUMN id integer;
SET client_min_messages TO fatal;
CREATE SEQUENCE spokenin_id_seq;
SET client_min_messages TO error;
ALTER TABLE SpokenIn ALTER COLUMN id
    SET DEFAULT nextval('spokenin_id_seq');
-- this is where we update the existing rows to get
-- a new id each
UPDATE SpokenIn SET id=DEFAULT;
-- now we can set the column not null and make it
-- the primary key, which is unique
ALTER TABLE SpokenIn ALTER COLUMN id SET NOT NULL;
ALTER TABLE SpokenIn DROP CONSTRAINT spokenin_pkey;
ALTER TABLE SpokenIn ADD PRIMARY KEY (id);


/* Add a serial primary key to SourcePackageRelationship */
SET client_min_messages=FATAL;
CREATE SEQUENCE sourcepackagerelationship_id_seq;
SET client_min_messages=ERROR;
ALTER TABLE SourcePackageRelationship ADD COLUMN id integer;
ALTER TABLE SourcePackageRelationship ALTER COLUMN id
    SET DEFAULT nextval('sourcepackagerelationship_id_seq');
UPDATE SourcePackageRelationship SET id=DEFAULT;
ALTER TABLE SourcePackageRelationship ALTER COLUMN id SET NOT NULL;
ALTER TABLE SourcePackageRelationship 
    DROP CONSTRAINT sourcepackagerelationship_pkey;
ALTER TABLE SourcePackageRelationship ADD PRIMARY KEY (id);

/* translatable was a false start - drop it */
ALTER TABLE Language DROP translatable;

/* SSH key store */
CREATE TABLE SSHKey (
    id          serial PRIMARY KEY,
    person      integer REFERENCES Person,
    keytype     integer NOT NULL,
    keytext     text NOT NULL,
    "comment"   text NOT NULL
    );
CREATE INDEX sshkey_person_key ON SSHKey(person);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=6, patch=0;
