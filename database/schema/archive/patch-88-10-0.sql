SET client_min_messages=ERROR;

ALTER TABLE HwSubmission
    ADD COLUMN raw_emailaddress text,
    ALTER COLUMN owner DROP NOT NULL;

CREATE INDEX hwsubmission__raw_emailaddress__idx
    ON HwSubmission(raw_emailaddress);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 10, 0);

