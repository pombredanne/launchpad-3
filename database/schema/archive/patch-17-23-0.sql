SET client_min_messages=ERROR;

ALTER TABLE POSubmission ADD COLUMN validationstatus integer;
UPDATE POSubmission SET validationstatus=0;
ALTER TABLE POSubmission ALTER COLUMN validationstatus SET NOT NULL;
ALTER TABLE POSubmission ALTER COLUMN validationstatus SET DEFAULT 0;

INSERT INTO LaunchpadDatabaseRevision VALUES  (17, 23, 0);
