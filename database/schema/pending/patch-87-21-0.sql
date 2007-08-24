BEGIN;

SET client_min_messages=ERROR;

-- DistroRelease table -> DistroSeries
ALTER TABLE DistroRelease RENAME TO DistroSeries;

ALTER TABLE distrorelease_id_seq RENAME TO distroseries_id_seq;
ALTER TABLE DistroSeries ALTER COLUMN id
    SET DEFAULT nextval('distroseries_id_seq');

ALTER TABLE distrorelease_pkey RENAME TO distroseries_pkey;
ALTER TABLE distrorelease_distribution_key
    RENAME TO distroseries__distribution__name__key;

ALTER TABLE distrorelease_distro_release_unique
    RENAME TO distroseries__distribution__id__key;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__distribution__fk
    FOREIGN KEY (distribution) REFERENCES Distribution;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_distribution_fk;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__driver__fk
    FOREIGN KEY (driver) REFERENCES Person;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_driver_fk;
CREATE INDEX distroseries__driver__idx ON DistroSeries(driver)
    WHERE driver IS NOT NULL;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__nominatedarchindep__fk
    FOREIGN KEY (nominatedarchindep) REFERENCES DistroArchRelease;
ALTER TABLE DistroSeries DROP CONSTRAINT distrorelease_nominatedarchindep_fk;

ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__owner__fk
    FOREIGN KEY (owner) REFERENCES Person;
ALTER  TABLE DistroSeries DROP CONSTRAINT distrorelease_owner_fk;
CREATE INDEX distroseries__owner__idx ON DistroSeries(owner);

ALTER TABLE DistroSeries RENAME COLUMN parentrelease TO parent_series;
ALTER TABLE DistroSeries ADD CONSTRAINT distroseries__parent_series__fk
    FOREIGN KEY (parent_series) REFERENCES DistroSeries;

-- DistroReleaseLanguage table -> DistroSeriesLanguage
ALTER TABLE DistroReleaseLanguage RENAME TO DistroSeriesLanguage;

ALTER TABLE distroreleaselanguage_id_seq RENAME TO distroserieslanguage_id_seq;
ALTER TABLE DistroSeriesLanguage ALTER COLUMN id
    SET DEFAULT nextval('distroserieslanguage_id_seq');

ALTER TABLE DistroSeriesLanguage RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroreleaselanguage_pkey RENAME TO distroserieslanguage_pkey;
ALTER TABLE distroreleaselanguage_distrorelease_language_uniq
    RENAME TO distroserieslanguage__distrorelease__language__key;
ALTER TABLE DistroSeriesLanguage
    ADD CONSTRAINT distroserieslanguage__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE DistroSeriesLanguage
    DROP CONSTRAINT distroreleaselanguage_distrorelease_fk;
ALTER TABLE DistroSeriesLanguage
    ADD CONSTRAINT distroserieslanguage__language__fk
    FOREIGN KEY (language) REFERENCES Language;

-- DistroArchRelease -> DistroArchSeries
ALTER TABLE DistroArchRelease RENAME TO DistroArchSeries;

ALTER TABLE distroarchrelease_id_seq RENAME TO distroarchseries_id_seq;
ALTER TABLE DistroArchSeries ALTER COLUMN id
    SET DEFAULT nextval('distroarchseries_id_seq');

ALTER TABLE DistroArchSeries RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroarchrelease_pkey RENAME TO distroarchseries_pkey;
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__architecturetag__distroseries__key
    UNIQUE (architecturetag, distroseries);
ALTER TABLE DistroArchSeries DROP CONSTRAINT
    distroarchrelease_distrorelease_architecturetag_unique;
DROP INDEX distroarchrelease_architecturetag_idx;
ALTER TABLE distroarchrelease_distrorelease_idx
    RENAME TO distroarchseries__distroseries__idx;
ALTER TABLE DistroArchSeries
    DROP CONSTRAINT distroarchrelease_distrorelease_processorfamily_unique;
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__processorfamily__distroseries__key
    UNIQUE (processorfamily, distroseries);
DROP INDEX distroarchrelease_processorfamily_idx;

ALTER TABLE DistroArchSeries ADD CONSTRAINT distroarchseries__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$1";
ALTER TABLE DistroArchSeries
    ADD CONSTRAINT distroarchseries__processorfamily__fk
    FOREIGN KEY (processorfamily) REFERENCES ProcessorFamily;
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$2";
ALTER TABLE DistroArchSeries ADD CONSTRAINT distroarchseries__owner__fk
    FOREIGN KEY (owner) REFERENCES Person;
CREATE INDEX distroarchseries__owner__idx ON DistroArchSeries(owner);
ALTER TABLE DistroArchSeries DROP CONSTRAINT "$3";

-- DistroReleasePackageCache -> DistroSeriesPackageCache
ALTER TABLE DistroReleasePackageCache RENAME TO DistroSeriesPackageCache;

ALTER TABLE distroreleasepackagecache_id_seq
    RENAME TO distroseriespackagecache_id_seq;
ALTER TABLE DistroSeriesPackageCache ALTER COLUMN id
    SET DEFAULT nextval('distroseriespackagecache');

ALTER TABLE DistroSeriesPackageCache
    RENAME COLUMN distrorelease TO distroseries;

ALTER TABLE distroreleasepackagecache_pkey
    RENAME TO distroseriespackagecache_pkey;
ALTER TABLE distroreleasepackagecache_fti
    RENAME TO distroseriespackagecache_fti;

ALTER TABLE DistroSeriesPackageCache
    ADD CONSTRAINT
    distroseriespackagecache__binarypackagename_distroseries__key
    UNIQUE (binarypackagename, distroseries),

    DROP CONSTRAINT
    distroreleasepackagecache_distrorelease_binarypackagename_uniq,

    DROP CONSTRAINT distroreleasepackagecache_binarypackagename_fk,

    ADD CONSTRAINT distroseriespackagecache__binarypackagename__fk
    FOREIGN KEY (binarypackagename) REFERENCES BinaryPackageName,

    DROP CONSTRAINT distroreleasepackagecache_distrorelease_fk,

    ADD CONSTRAINT distroseriespackagecache__distroseries__fk
    FOREIGN KEY (distroseries) REFERENCES DistroSeries;

CREATE INDEX distroseriespackagecache__distroseries__idx
    ON DistroSeriesPackageCache(distroseries);


-- BugNomination
ALTER TABLE BugNomination RENAME COLUMN distrorelease TO distroseries;
ALTER TABLE BugNomination
    DROP CONSTRAINT bugnomination__distrorelease__fk,
    ADD CONSTRAINT bugnomination__distroseries__fk
        FOREIGN KEY (distroseries) REFERENCES DistroSeries;

\d BugNomination

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 21, 0);
ABORT;
