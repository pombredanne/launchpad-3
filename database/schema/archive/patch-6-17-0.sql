
/*
  We need to give the SpokenIn table a primary key id. What makes this fun
  is that there is already data in there. Hence the UPDATE to set each row
  to have a unique ID.

*/

ALTER TABLE ProductReleaseFile ADD COLUMN id integer;
SET client_min_messages TO fatal;
CREATE SEQUENCE productreleasefile_id_seq;
SET client_min_messages TO error;
ALTER TABLE ProductReleaseFile ALTER COLUMN id
    SET DEFAULT nextval('productreleasefile_id_seq');
-- this is where we update the existing rows to get
-- a new id each
UPDATE ProductReleaseFile SET id=DEFAULT;
-- now we can set the column not null and make it
-- the primary key, which is unique
ALTER TABLE ProductReleaseFile ALTER COLUMN id SET NOT NULL;
ALTER TABLE ProductReleaseFile ADD PRIMARY KEY (id);

UPDATE LaunchpadDatabaseRevision SET major=6, minor=17, patch=0;
