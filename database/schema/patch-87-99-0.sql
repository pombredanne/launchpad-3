SET client_min_messages=ERROR;

-- Allow HWSubmission records with person set to null in order to avoid
-- cluttering of the Person table with lots automatically generated rows
-- which will never become active Launchpad accounts.

ALTER TABLE HWSubmission ADD COLUMN raw_emailaddress text NOT NULL;
ALTER TABLE HWSubmission ALTER COLUMN owner DROP NOT NULL;
CREATE INDEX HWSubmission__raw_emailaddress__idx 
    ON HWSubmission(raw_emailaddress);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
