SET client_min_messages=ERROR;

-- Guarantee builds are created in separated transactions.

ALTER TABLE Build
    ADD CONSTRAINT build__datecreated__key UNIQUE (datecreated);

INSERT INTO LaunchpadDatabaseRevision VALUES (121,76, 0);
