SET client_min_messages=ERROR;

ALTER TABLE LibraryFileAlias
    ADD COLUMN restricted BOOLEAN DEFAULT False NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 22, 0);
