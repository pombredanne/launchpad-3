SET client_min_messages=ERROR;

/* Add an id column */

ALTER TABLE Packaging ADD COLUMN id integer;
CREATE SEQUENCE packaging_id_seq;
ALTER TABLE Packaging ALTER COLUMN id SET DEFAULT nextval('packaging_id_seq'); 


INSERT INTO LaunchpadDatabaseRevision VALUES (10,2,0);

