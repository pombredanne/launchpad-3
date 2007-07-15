BEGIN;

SET client_min_messages=ERROR;

-- Rename DistroRelease table
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

\d distroseries
        
ALTER TABLE DistroReleaseLanguage RENAME TO DistroSeriesLanguage;
ALTER TABLE DistroSeriesLanguage RENAME COLUMN distrorelease TO distroseries;


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 21, 0);

ABORT;
