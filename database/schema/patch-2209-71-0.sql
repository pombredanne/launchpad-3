-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE DistroSeries ADD COLUMN publishing_options text;

COMMENT ON COLUMN DistroSeries.publishing_options IS 'A JSON object containing options modifying the publisher''s behaviour for this series.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 71, 0);
