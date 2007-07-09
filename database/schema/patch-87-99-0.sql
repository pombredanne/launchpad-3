/*
 * This patch adds support for the upcoming commercial archive.
 * Distribution.main_archive has gone, and Archive has new distribution and
 * purpose columns, which collectively define an archive's raison d'etre.
 */
   
SET client_min_messages=ERROR;
   
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

-- This row needs to be inserted into production after landing, the lack
-- of sample data when running the patch hits the distribution constraint.
--INSERT INTO Archive (description, distribution, purpose)
--    VALUES ('Commercial archive', 1, 4);

-- New commercial component
INSERT INTO component (id, name, description)
    VALUES (5, 'commercial', 'This component contains commercial packages only, which are not in the main Ubuntu archive.');

-- Also create componentselection rows to allow "commercial" for Gutsy 
-- distroseries.

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
