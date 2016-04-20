-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE SnapSeries (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    name text NOT NULL,
    display_name text NOT NULL,
    status integer NOT NULL
);

CREATE UNIQUE INDEX snapseries__name__key ON SnapSeries(name);

COMMENT ON TABLE SnapSeries IS 'A series for snap packages in the store.';
COMMENT ON COLUMN SnapSeries.date_created IS 'The date on which this series was created in Launchpad.';
COMMENT ON COLUMN SnapSeries.registrant IS 'The user who registered this series.';
COMMENT ON COLUMN SnapSeries.name IS 'The unique name of this series.';
COMMENT ON COLUMN SnapSeries.display_name IS 'The display name of this series.';
COMMENT ON COLUMN SnapSeries.status IS 'The current status of this series.';

CREATE TABLE SnapDistroSeries (
    snap_series integer NOT NULL REFERENCES snapseries,
    distro_series integer NOT NULL REFERENCES distroseries,
    PRIMARY KEY (snap_series, distro_series)
);

COMMENT ON TABLE SnapDistroSeries IS 'A record indicating that a particular snap series is valid for builds from a particular distribution series.';
COMMENT ON COLUMN SnapDistroSeries.snap_series IS 'The snap series which is valid for builds from this distribution series.';
COMMENT ON COLUMN SnapDistroSeries.distro_series IS 'The distribution series whose builds are valid for this snap series.';

ALTER TABLE Snap
    ADD COLUMN store_upload boolean DEFAULT false NOT NULL,
    ADD COLUMN store_series integer REFERENCES snapseries,
    ADD COLUMN store_name text,
    ADD COLUMN store_tokens text,
    ADD CONSTRAINT consistent_store_upload CHECK (
        NOT store_upload
        OR (store_series IS NOT NULL AND store_name IS NOT NULL));

COMMENT ON COLUMN Snap.store_upload IS 'Whether builds of this snap package are automatically uploaded to the store.';
COMMENT ON COLUMN Snap.store_series IS 'The series in which this snap package should be published in the store.';
COMMENT ON COLUMN Snap.store_name IS 'The registered name of this snap package in the store.';
COMMENT ON COLUMN Snap.store_tokens IS 'Serialized tokens issued by the store and the login service to authorize uploads of this snap package.';

CREATE INDEX snap__store_series__idx ON Snap(store_series) WHERE store_series IS NOT NULL;

ALTER TABLE SnapBuild ADD COLUMN store_upload_status integer;

CREATE INDEX snapbuild__store_upload_status__idx ON SnapBuild(store_upload_status) WHERE store_upload_status IS NOT NULL;

COMMENT ON COLUMN SnapBuild.store_upload_status IS 'The status of uploading this build to the store.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 3);
