SET client_min_messages=ERROR;

-- staging: 16 rows, 46s
INSERT INTO Language
  (code, englishname, pluralforms, pluralexpression, direction, visible)
  SELECT
      language.code || '@' || variant AS full_code,
      language.englishname || ' (' || variant || ')' AS full_name,
      language.pluralforms,
      language.pluralexpression,
      language.direction,
      False
    FROM translationmessage
    JOIN language
      ON language=language.id
    WHERE variant IS NOT NULL
  UNION
  SELECT
      language.code || '@' || variant,
      language.englishname || ' (' || variant || ')' AS full_name,
      language.pluralforms,
      language.pluralexpression,
      language.direction,
      False
    FROM pofile
    JOIN language
      ON language=language.id
    WHERE variant IS NOT NULL;

-- staging: 850000 rows, ...
UPDATE translationmessage
  SET language=(
      SELECT id FROM language
        WHERE code=old_language.code || '@' || variant)
  FROM language AS old_language
  WHERE
    translationmessage.language=old_language.id AND
    variant IS NOT NULL;

-- staging: 13029 rows, 22s
UPDATE pofile
  SET language=(
      SELECT id FROM language
        WHERE code=old_language.code || '@' || variant)
  FROM language AS old_language
  WHERE
    pofile.language=old_language.id AND
    variant IS NOT NULL;

ALTER TABLE TranslationMessage
    DROP COLUMN variant;
ALTER TABLE POFile
    DROP COLUMN variant;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 94, 0);
