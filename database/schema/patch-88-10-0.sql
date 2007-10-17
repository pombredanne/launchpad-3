SET client_min_messages=ERROR;

ALTER TABLE HwSubmission
    ADD COLUMN raw_emailaddress text,
    ALTER COLUMN owner DROP NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 10, 0);

