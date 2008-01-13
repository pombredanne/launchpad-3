SET client_min_messages=ERROR;

-- Make NOT NULL DEFAULT=FALSE when fully populated
ALTER TABLE Person ADD COLUMN verbose_bugnotifications boolean;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 42, 4);
