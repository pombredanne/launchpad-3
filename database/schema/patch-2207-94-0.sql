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
          WHERE code=old_language.code || '@' || variant),
      variant=NULL
  FROM language AS old_language
  WHERE
    translationmessage.language=old_language.id AND
    variant IS NOT NULL;

-- staging: 13029 rows, 22s
UPDATE pofile
  SET language=(
        SELECT id FROM language
          WHERE code=old_language.code || '@' || variant),
      variant=NULL
  FROM language AS old_language
  WHERE
    pofile.language=old_language.id AND
    variant IS NOT NULL;

ALTER TABLE TranslationMessage
    DROP COLUMN variant;
ALTER TABLE POFile
    DROP COLUMN variant;


-- Recreate indexes that used variant in the past.

CREATE UNIQUE INDEX pofile_template_and_language_idx
   ON pofile USING btree (potemplate, language);

CREATE UNIQUE INDEX tm__potmsgset__language__shared__current__key ON translationmessage USING btree (potmsgset, language) WHERE (((is_current IS TRUE) AND (potemplate IS NULL)));

CREATE UNIQUE INDEX tm__potmsgset__language__shared__imported__key ON translationmessage USING btree (potmsgset, language) WHERE (((is_imported IS TRUE) AND (potemplate IS NULL)));

CREATE INDEX tm__potmsgset__language__not_used__idx ON translationmessage USING btree (potmsgset, language) WHERE (NOT ((is_current IS TRUE) AND (is_imported IS TRUE)));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__diverged__current__idx ON translationmessage USING btree (potmsgset, potemplate, language) WHERE (((is_current IS TRUE) AND (potemplate IS NOT NULL)));

CREATE UNIQUE INDEX tm__potmsgset__potemplate__language__diverged__imported__idx ON translationmessage USING btree (potmsgset, potemplate, language) WHERE (((is_imported IS TRUE) AND (potemplate IS NOT NULL)));

CREATE INDEX translationmessage__language__submitter__idx ON translationmessage USING btree (language, submitter);


INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 94, 0);
