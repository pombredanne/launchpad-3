
/*
  We need to give the SpokenIn table a primary key id. What makes this fun
  is that there is already data in there. Hence the UPDATE to set each row
  to have a unique ID.

  Stub: this is good to go.
  
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


