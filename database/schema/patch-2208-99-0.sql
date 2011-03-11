-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Renaming owner to registrant for
-- DistroSeries
BEGIN;

-- Add a registrant column to DistroSeries.
ALTER TABLE DistroSeries
    ADD COLUMN registrant integer REFERENCES Person;

-- Migrate owner to registrant.
UPDATE DistroSeries
    SET registrant = owner;

-- Kill the old column.
ALTER TABLE DistroSeries
    DROP COLUMN owner;

-- Add NOT NULL constraint to registrant column.
ALTER TABLE DistroSeries ALTER COLUMN registrant SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

COMMIT;
