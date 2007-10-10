SET client_min_messages=ERROR;

UPDATE Person SET account_status = 10 WHERE teamowner IS NOT NULL;

ALTER TABLE Person ADD CONSTRAINT valid_team_account_status
    CHECK (teamowner IS NULL OR account_status = 10);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 01, 0);
