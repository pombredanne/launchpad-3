SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN bugnotification_include_description bool NOT NULL DEFAULT true;
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
