-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

BEGIN;

-- Add a registrant column to distributions.
ALTER TABLE Distribution
    ADD COLUMN registrant integer REFERENCES Person;

-- Set registrant to ~registry for existing distros.
update Distribution
    SET registrant = (select id from Person where name='registry');

-- Add NOT NULL constraint to registrant column.
ALTER TABLE Distribution  ALTER COLUMN registrant SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

COMMIT;
