-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SnappyDistroSeries ADD COLUMN preferred boolean DEFAULT false NOT NULL;

CREATE UNIQUE INDEX snappydistroseries__snappy_series__preferred__idx ON SnappyDistroSeries (snappy_series) WHERE preferred;

COMMENT ON COLUMN SnappyDistroSeries.preferred IS 'True if this record identifies the default distribution series for builds for this snappy series.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 6);
