SET client_min_messages=ERROR;

ALTER TABLE person ADD COLUMN account_status_comment text;
-- The default value used here is different than what we use on python code
-- because we'd need around 6h to update all valid accounts changing their
-- statuses. This is going to be solved once I get some time to fix
-- https://bugs.launchpad.net/launchpad/+bug/123770.
ALTER TABLE person ADD COLUMN account_status integer DEFAULT 20;

UPDATE person
    SET account_status = 10
    WHERE id NOT IN (SELECT id FROM ValidPersonOrTeamCache)
        OR teamowner IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 22, 0);
