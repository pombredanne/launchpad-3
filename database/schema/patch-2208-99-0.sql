-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Add a column to order DSP (this will allow controlling of the build
-- order for overlays).
ALTER TABLE DistroSeriesParent
    ADD COLUMN ordering INTEGER NOT NULL DEFAULT 1;

-- Update existing DSPs.
UPDATE DistroSeriesParent
    SET ordering = 1;

-- Create index.
CREATE INDEX distroseriesparent__ordering
    ON DistroSeriesParent (ordering);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
