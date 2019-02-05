-- Copyright 2019 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BaseSnap (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    name text NOT NULL,
    display_name text NOT NULL,
    distro_series integer NOT NULL REFERENCES distroseries,
    channels text NOT NULL,
    is_default boolean NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE UNIQUE INDEX basesnap__name__key ON BaseSnap (name);
CREATE INDEX basesnap__registrant__idx ON BaseSnap (registrant);
CREATE UNIQUE INDEX basesnap__is_default__idx ON BaseSnap (is_default) WHERE is_default;

COMMENT ON TABLE BaseSnap IS 'A base snap.';
COMMENT ON COLUMN BaseSnap.date_created IS 'The date on which this base snap was created in Launchpad.';
COMMENT ON COLUMN BaseSnap.registrant IS 'The user who registered this base snap.';
COMMENT ON COLUMN BaseSnap.name IS 'The unique name of this base snap.';
COMMENT ON COLUMN BaseSnap.display_name IS 'The display name of this base snap.';
COMMENT ON COLUMN BaseSnap.distro_series IS 'The distro series used for snap builds that specify this base snap.';
COMMENT ON COLUMN BaseSnap.channels IS 'A dictionary mapping snap names to channels to use when building snaps that specify this base snap.';
COMMENT ON COLUMN BaseSnap.is_default IS 'Whether this base snap indicates the defaults used for snap builds that do not specify a base snap.';

-- Allow defining snap recipes that detect the distro series from
-- snapcraft.yaml.
ALTER TABLE Snap ALTER COLUMN distro_series DROP NOT NULL;

-- Allow combined vocabularies of (store_series, distro_series) pairs to
-- include entries for a store series without a distro series.  Columns that
-- are part of a primary key cannot be NULL, so replace the natural primary
-- key with a surrogate.
ALTER TABLE SnappyDistroSeries
    ADD COLUMN id serial,
    DROP CONSTRAINT snappydistroseries_pkey,
    ADD PRIMARY KEY (id),
    ALTER COLUMN distro_series DROP NOT NULL;
CREATE UNIQUE INDEX snappydistroseries__snappy_series__distro_series__idx
    ON SnappyDistroSeries (snappy_series, distro_series);
CREATE UNIQUE INDEX snappydistroseries__snappy_series__guess_distro_series__idx
    ON SnappyDistroSeries (snappy_series) WHERE distro_series IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 83, 6);
