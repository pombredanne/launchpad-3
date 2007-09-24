SET client_min_messages=ERROR;

UPDATE Person
SET account_status = 10
WHERE teamowner IS NULL;

ALTER TABLE Person
ADD CONSTRAINT teams_have_no_account
    CHECK (teamowner IS NULL OR account_status = 10);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 88, 0);
