--CREATE TABLE distributionarchive (
--    id integer NOT NULL,
--    distribution integer NOT NULL,
--    archive integer NOT NULL,
--    purpose integer NOT NULL
--);

--ALTER TABLE ONLY distributionarchive
--    ADD CONSTRAINT distributionarchive_pkey PRIMARY KEY (id);

-- CREATE UNIQUE INDEX distributionarchive__distribution__archive__uniq ON distributionarchive USING btree (distribution, archive);

--ALTER TABLE ONLY distributionarchive
--    ADD CONSTRAINT distributionarchive_distribution_fk FOREIGN KEY (distribution) REFERENCES distribution(id);

--ALTER TABLE ONLY distributionarchive
--    ADD CONSTRAINT distributionarchive_archive_fk FOREIGN KEY (archive) REFERENCES archive(id);


ALTER TABLE distribution DROP COLUMN main_archive;
ALTER TABLE archive ADD COLUMN distribution INTEGER;
ALTER TABLE archive ADD COLUMN purpose INTEGER;
ALTER TABLE ONLY archive
    ADD CONSTRAINT archive_distribution_fk 
    FOREIGN KEY (distribution) REFERENCES distribution(id);

-- add btree for distro/purpose on archive, owner required to make it
-- unique for PPAs where distro is not set.
CREATE UNIQUE INDEX archive__distribution__purpose__uniq ON archive 
    USING btree(distribution, purpose, owner);

ALTER TABLE component ADD COLUMN description TEXT;

-- Some existing archive rows are PPA
UPDATE Archive SET purpose = 2 where OWNER IS NOT NULL;
UPDATE Archive SET distribution = 1 where OWNER IS NOT NULL;
-- The other archive rows are the main archive
UPDATE Archive SET distribution = id where OWNER IS NULL;
UPDATE Archive SET purpose = 1 where OWNER IS NULL;
ALTER TABLE archive ALTER COLUMN purpose SET NOT NULL;

-- uncomment this before landing in PQM
-- Add commercial archive for Ubuntu
--INSERT INTO Archive (description, distribution, purpose)
--    VALUES ('Commercial archive', '1', 4);

-- New commercial component
--INSERT INTO component (name, description)
--    VALUES ('commercial', 'This component contains commercial packages only, which are not in the main Ubuntu archive.');


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
