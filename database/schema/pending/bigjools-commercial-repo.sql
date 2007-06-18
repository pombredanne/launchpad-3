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


-- Schema changes

ALTER TABLE archive ADD COLUMN path TEXT;
ALTER TABLE archive ADD COLUMN distribution INTEGER;
ALTER TABLE archive ADD COLUMN purpose INTEGER NOT NULL;
ALTER TABLE ONLY archive
    ADD CONSTRAINT archive_distribution_fk 
    FOREIGN KEY (distribution) REFERENCES distribution(id);

-- add btree for distro/purpose on archive, owner required to make it
-- unique for PPAs where distro is not set.
CREATE UNIQUE INDEX archive__distribution__purpose__uniq ON archive 
    USING btree(distribution, purpose, owner);


ALTER TABLE component ADD COLUMN description TEXT;


-- Data changes

-- All existing archive rows are currently PPA
UPDATE Archive SET purpose = 2;
-- Add commercial archive for Ubuntu
INSERT INTO Archive (description, path, distribution, purpose)
    VALUES ("Commercial archive", "/tmp", 1, 4)

-- New commercial component
INSERT INTO component (name, description)
    VALUES ("commercial", "The commercial component.  Packages for this component are not in the main Ubuntu archive.")
