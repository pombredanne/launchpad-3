SET client_min_messages=ERROR;

-- Adding a summary field to Archive.

ALTER TABLE Archive ADD COLUMN summary text;


-- Indexing Archive summary and description. It will require us to update
-- the indexes for the pre-existing records.

ALTER TABLE Archive ADD COLUMN fti ts2.tsvector;
CREATE INDEX archive_fti ON archive USING gist (fti ts2.gist_tsvector_ops);
CREATE TRIGGER tsvectorupdate
    BEFORE INSERT OR UPDATE ON archive
    FOR EACH ROW
    EXECUTE PROCEDURE ts2.ftiupdate('summary', 'a', 'description', 'b');


-- Add 'archive' column to the DistributionSourcePackageCache and
-- DistroSeriesPackageCache. The can become NOT NULL after the first run
-- update-pkgcache script since it will fill this column appropriately.

ALTER TABLE DistributionSourcePackageCache
    ADD COLUMN archive integer;
ALTER TABLE DistributionSourcePackageCache ADD CONSTRAINT
    distributionsourcepackagecache__archive__fk
    FOREIGN KEY (archive) REFERENCES Archive;

ALTER TABLE DistroSeriesPackageCache
    ADD COLUMN archive integer;
ALTER TABLE DistroSeriesPackageCache ADD CONSTRAINT
    distroseriespackagecache__archive__fk
    FOREIGN KEY (archive) REFERENCES Archive;


-- Extend the unique constraint to cover parallel development of the same
-- source across archives (PPAs).

ALTER TABLE DistributionSourcePackageCache DROP CONSTRAINT
    distributionsourcepackagecache_distribution_sourcepackagename_u;
ALTER TABLE DistributionSourcePackageCache ADD CONSTRAINT
    distributionsourcepackagecache_distribution_sourcepackagename_archive_u
    UNIQUE(distribution, sourcepackagename, archive);

ALTER TABLE DistroSeriesPackageCache DROP CONSTRAINT
    distroseriespackagecache__binarypackagename_distroseries__key;
ALTER TABLE DistroSeriesPackageCache ADD CONSTRAINT
    distroseriespackagecache_distroseries_binarypackagename_archive_u
    UNIQUE(distroseries, binarypackagename, archive);


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
