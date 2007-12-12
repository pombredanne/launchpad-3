SET client_min_messages=DEBUG;

-- Some constraints looked like they had been renamed, but in fact just
-- their indexes had been. This breaks slony-I. We put them back the
-- way they where as renaming the primary key names properly is way to
-- involved, dangerous and slow. Wait until PG supports renaming constraints.

ALTER TABLE distroarchseries_pkey RENAME TO distroarchrelease_pkey;
ALTER TABLE distroseries_pkey RENAME TO distrorelease_pkey;
ALTER TABLE distroserieslanguage_pkey RENAME TO distroreleaselanguage_pkey;
ALTER TABLE distroseriespackagecache_pkey
    RENAME TO distroreleasepackagecache_pkey;
ALTER TABLE packageupload_pkey RENAME TO distroreleasequeue_pkey;
ALTER TABLE packageuploadbuild_pkey RENAME TO distroreleasequeuebuild_pkey;
ALTER TABLE packageuploadcustom_pkey
    RENAME TO distroreleasequeuecustom_pkey;
ALTER TABLE packageuploadsource_pkey
    RENAME TO distroreleasequeuesource_pkey;
ALTER TABLE mirrorcdimagedistroseries_pkey
    RENAME TO mirrorcdimagedistrorelease_pkey;
ALTER TABLE mirrordistroseriessource_pkey
    RENAME TO mirrordistroreleasesource_pkey;
ALTER TABLE mirrordistroarchseries_pkey
    RENAME TO mirrordistroarchrelease_pkey;
    
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 31, 0);
