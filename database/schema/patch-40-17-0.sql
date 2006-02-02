SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN hide_email_addresses boolean;
ALTER TABLE Person ALTER COLUMN hide_email_addresses SET DEFAULT FALSE;

UPDATE Person SET hide_email_addresses = FALSE;

ALTER TABLE Person ALTER COLUMN hide_email_addresses SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 17, 0);

