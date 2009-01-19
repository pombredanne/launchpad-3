SET client_min_messages=ERROR;

-- Provide per-project and per-team translation style guide URLs.

ALTER TABLE TranslationGroup ADD COLUMN translation_guide_url text;
ALTER TABLE Translator ADD COLUMN style_guide_url text;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

