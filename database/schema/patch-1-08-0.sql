SET client_min_messages TO error;
/* Add serial primary keys to DistributionRole and DistroreleaseRole 
   for celso
 */

ALTER TABLE DistributionRole ADD COLUMN id integer;
ALTER TABLE DistroreleaseRole ADD COLUMN id integer;

SET client_min_messages TO fatal;
CREATE SEQUENCE DistributionRole_id_seq;
CREATE SEQUENCE DistroreleaseRole_id_seq;
SET client_min_messages TO error;

UPDATE DistributionRole SET id=nextval('DistributionRole_id_seq');
UPDATE DistroreleaseRole SET id=nextval('DistroreleaseRole_id_seq');

ALTER TABLE DistributionRole ADD PRIMARY KEY (id);
ALTER TABLE DistroreleaseRole ADD PRIMARY KEY (id);

ALTER TABLE DistributionRole ALTER COLUMN id 
    SET DEFAULT nextval('DistributionRole_id_seq');
ALTER TABLE DistroreleaseRole ALTER COLUMN id 
    SET DEFAULT nextval('DistroreleaseRole_id_seq');


/* Another name constraint - need to comb the database and do these in
   a batch :-(
*/
ALTER TABLE SourcepackageName ADD CONSTRAINT lowercasename 
    CHECK (lower(name) = name);

