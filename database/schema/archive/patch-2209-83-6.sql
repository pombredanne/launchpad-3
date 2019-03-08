-- Copyright 2019 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE SnapBase (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer NOT NULL REFERENCES person,
    name text NOT NULL,
    display_name text NOT NULL,
    distro_series integer NOT NULL REFERENCES distroseries,
    build_channels text NOT NULL,
    is_default boolean NOT NULL,
    CONSTRAINT valid_name CHECK (valid_name(name))
);

CREATE UNIQUE INDEX snapbase__name__key ON SnapBase (name);
CREATE INDEX snapbase__registrant__idx ON SnapBase (registrant);
CREATE UNIQUE INDEX snapbase__is_default__idx ON SnapBase (is_default) WHERE is_default;

COMMENT ON TABLE SnapBase IS 'A base for snaps.';
COMMENT ON COLUMN SnapBase.date_created IS 'The date on which this base was created in Launchpad.';
COMMENT ON COLUMN SnapBase.registrant IS 'The user who registered this base.';
COMMENT ON COLUMN SnapBase.name IS 'The unique name of this base.';
COMMENT ON COLUMN SnapBase.display_name IS 'The display name of this base.';
COMMENT ON COLUMN SnapBase.distro_series IS 'The distro series used for snap builds that specify this base.';
COMMENT ON COLUMN SnapBase.build_channels IS 'A dictionary mapping snap names to channels to use when building snaps that specify this base.';
COMMENT ON COLUMN SnapBase.is_default IS 'Whether this base is the default for snaps that do not specify a base.';

-- Allow defining snap recipes that infer the distro series from
-- snapcraft.yaml.
ALTER TABLE Snap ALTER COLUMN distro_series DROP NOT NULL;

-- Allow combined vocabularies of (store_series, distro_series) pairs to
-- include entries for a store series without a distro series, allowing
-- straightforward UI configuration of snaps that infer the distro series
-- from snapcraft.yaml.  Columns that are part of a primary key cannot be
-- NULL, so replace the natural primary key with a surrogate.
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
