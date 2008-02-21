SET client_min_messages=ERROR;

ALTER TABLE CodeImport ADD COLUMN
    date_last_successful TIMESTAMP WITHOUT TIME ZONE;

/* DBA set a real db patch number on review. -- David Allouche 2007-07-03. */
INSERT INTO LaunchpadDatabaseRevision VALUES (87, 29, 0);

