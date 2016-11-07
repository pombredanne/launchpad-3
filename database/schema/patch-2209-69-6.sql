-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE SnappySeries ADD COLUMN preferred_distro_series integer REFERENCES distroseries;

COMMENT ON COLUMN SnappySeries.preferred_distro_series IS 'The preferred distribution series for use with this snappy series.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 69, 6);
