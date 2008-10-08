SET client_min_messages=ERROR;

-- Adding text blob location to represent PPA context on searchs amongst
-- all other PPAs.

ALTER TABLE Archive
    ADD COLUMN sources_cached integer,
    ADD COLUMN binaries_cached integer,
    ADD COLUMN package_description_cache text;

-- Indexing Archive package_description_text and description. It will
-- require us to update the indexes for the pre-existing records.

-- fti.py maintains this column for us.
--
-- ALTER TABLE Archive ADD COLUMN fti ts2.tsvector;
-- CREATE INDEX archive_fti ON archive USING gist (fti ts2.gist_tsvector_ops);
-- CREATE TRIGGER tsvectorupdate
--     BEFORE INSERT OR UPDATE ON archive
--     FOR EACH ROW
--     EXECUTE PROCEDURE ts2.ftiupdate(
--         'description', 'a', 'packagedescriptioncache', 'b');


-- Add 'archive' column to the DistributionSourcePackageCache and
-- DistroSeriesPackageCache. The can become NOT NULL after the first run
-- update-pkgcache script since it will fill this column appropriately.

-- Update all caches to point to the ubuntu PRIMARY archive.
-- The pre-existing ones which belongs to the PARTNER archive will be
-- removed and re-created in the first update-pkgcache.py run.

-- Extend the unique constraint to cover parallel development of the same
-- source across archives (PPAs).

ALTER TABLE DistributionSourcePackageCache
    ADD COLUMN archive integer,
    DROP CONSTRAINT
        distributionsourcepackagecache_distribution_sourcepackagename_u;
UPDATE DistributionSourcePackageCache set archive=(
    SELECT Archive.id FROM Archive, Distribution
    WHERE Distribution.id = Archive.distribution
        AND Archive.purpose = 1 AND Distribution.name='ubuntu'
    );
CREATE INDEX distributionsourcepackagecache__archive__idx
    ON DistributionSourcePackageCache(archive);
ALTER TABLE DistributionSourcePackageCache
    ADD CONSTRAINT distributionsourcepackagecache__archive__fk
    FOREIGN KEY (archive) REFERENCES Archive,
    ADD CONSTRAINT
        distributionsourcepackagecache__distribution__sourcepackagename__archive__key
        UNIQUE(distribution, sourcepackagename, archive);

ALTER TABLE DistroSeriesPackageCache
    ADD COLUMN archive integer,
    DROP CONSTRAINT
        distroseriespackagecache__binarypackagename_distroseries__key;
UPDATE DistroSeriesPackageCache set archive=(
    SELECT Archive.id FROM Archive, Distribution
    WHERE Distribution.id = Archive.distribution
        AND Archive.purpose = 1 AND Distribution.name='ubuntu'
    );
CREATE INDEX distroseriespackagecache__archive__idx
    ON DistroSeriesPackageCache(archive);
ALTER TABLE DistroSeriesPackageCache
    ADD CONSTRAINT distroseriespackagecache__archive__fk
    FOREIGN KEY (archive) REFERENCES Archive,
    ADD CONSTRAINT
    distroseriespackagecache__distroseries__binarypackagename__archive__key
    UNIQUE(distroseries, binarypackagename, archive);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 6, 0);
