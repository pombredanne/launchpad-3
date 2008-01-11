SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN verbose_bugnotifications bool NOT NULL DEFAULT true;
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
