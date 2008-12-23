SET client_min_messages=ERROR;

ALTER TABLE TranslationImportQueueEntry ADD COLUMN error_output text;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 7, 0);

