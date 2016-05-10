-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE SnappySeries (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    name text NOT NULL,
    display_name text NOT NULL,
    status integer NOT NULL
);

CREATE UNIQUE INDEX snappyseries__name__key ON SnappySeries(name);
CREATE INDEX snappyseries__registrant__idx ON SnappySeries(registrant);
CREATE INDEX snappyseries__status__idx ON SnappySeries(status);

COMMENT ON TABLE SnappySeries IS 'A series for snap packages in the store.';
COMMENT ON COLUMN SnappySeries.date_created IS 'The date on which this series was created in Launchpad.';
COMMENT ON COLUMN SnappySeries.registrant IS 'The user who registered this series.';
COMMENT ON COLUMN SnappySeries.name IS 'The unique name of this series.';
COMMENT ON COLUMN SnappySeries.display_name IS 'The display name of this series.';
COMMENT ON COLUMN SnappySeries.status IS 'The current status of this series.';

CREATE TABLE SnappyDistroSeries (
    snappy_series integer NOT NULL REFERENCES snappyseries,
    distro_series integer NOT NULL REFERENCES distroseries,
    PRIMARY KEY (snappy_series, distro_series)
);

CREATE INDEX snappydistroseries__distro_series__idx ON SnappyDistroSeries(distro_series);

COMMENT ON TABLE SnappyDistroSeries IS 'A record indicating that a particular snappy series is valid for builds from a particular distribution series.';
COMMENT ON COLUMN SnappyDistroSeries.snappy_series IS 'The snappy series which is valid for builds from this distribution series.';
COMMENT ON COLUMN SnappyDistroSeries.distro_series IS 'The distribution series whose builds are valid for this snappy series.';

ALTER TABLE Snap
    ADD COLUMN store_upload boolean DEFAULT false NOT NULL,
    ADD COLUMN store_series integer REFERENCES snappyseries,
    ADD COLUMN store_name text,
    ADD COLUMN store_secrets text,
    ADD CONSTRAINT consistent_store_upload CHECK (
        NOT store_upload
        OR (store_series IS NOT NULL AND store_name IS NOT NULL));

COMMENT ON COLUMN Snap.store_upload IS 'Whether builds of this snap package are automatically uploaded to the store.';
COMMENT ON COLUMN Snap.store_series IS 'The series in which this snap package should be published in the store.';
COMMENT ON COLUMN Snap.store_name IS 'The registered name of this snap package in the store.';
COMMENT ON COLUMN Snap.store_secrets IS 'Serialized secrets issued by the store and the login service to authorize uploads of this snap package.';

CREATE INDEX snap__store_series__idx
    ON Snap(store_series) WHERE store_series IS NOT NULL;

CREATE TABLE SnapBuildJob (
    job integer PRIMARY KEY REFERENCES Job ON DELETE CASCADE NOT NULL,
    snapbuild integer REFERENCES SnapBuild NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
);

CREATE INDEX snapbuildjob__snapbuild__job_type__job__idx
    ON SnapBuildJob(snapbuild, job_type, job);

COMMENT ON TABLE SnapBuildJob IS 'Contains references to jobs that are executed for a build of a snap package.';
COMMENT ON COLUMN SnapBuildJob.job IS 'A reference to a Job row that has all the common job details.';
COMMENT ON COLUMN SnapBuildJob.snapbuild IS 'The snap build that this job is for.';
COMMENT ON COLUMN SnapBuildJob.job_type IS 'The type of a job, such as a store upload.';
COMMENT ON COLUMN SnapBuildJob.json_data IS 'Data that is specific to a particular job type.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 3);
