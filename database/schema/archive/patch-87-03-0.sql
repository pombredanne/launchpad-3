SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN renewal_policy integer DEFAULT 10 NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 03, 0);
