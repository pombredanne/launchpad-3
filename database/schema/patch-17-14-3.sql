
-- Add some constraints to POFile

CREATE UNIQUE INDEX pofile_template_and_language_idx
    ON POFile (potemplate, language, (coalesce(variant, '')));
ALTER TABLE POFile ADD CONSTRAINT valid_variant CHECK (variant <> '');


INSERT INTO LaunchpadDatabaseRevision VALUES (17, 14, 3);
