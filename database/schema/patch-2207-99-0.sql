SET client_min_messages=ERROR;

ALTER TABLE TranslationMessage
RENAME is_current TO is_current_ubuntu;
ALTER TABLE TranslationMessage
RENAME is_imported TO is_current_upstream;

-- XXX: Update patch number!
INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0)
