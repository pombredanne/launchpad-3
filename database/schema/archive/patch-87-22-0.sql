SET client_min_messages=ERROR;

ALTER TABLE person ADD COLUMN account_status_comment text;
-- The default value used here is different than what we use on python code
-- because we'd need around 6h to update all valid accounts changing their
-- statuses. This is going to be solved once I get some time to fix
-- https://bugs.launchpad.net/launchpad/+bug/123770.

-- This column needs to be set NOT NULL and DEFAULT 10 next cycle.
-- The values need to be populated by then.
ALTER TABLE Person ADD COLUMN account_status integer;

/*
UPDATE Person
    SET account_status = 20
    FROM ValidPersonOrTeamCache
    WHERE Person.id = ValidPersonOrTeamCache.id
        AND teamowner IS NULL;

UPDATE Person
    SET account_status = 10
    WHERE account_status IS NULL;

ALTER TABLE Person ALTER COLUMN account_status SET NOT NULL;
ALTER TABLE Person ALTER COLUMN account_status SET DEFAULT 10;
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 22, 0);
