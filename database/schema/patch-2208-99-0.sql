-- migrate-official-bool-data sets the _usage enum database columns based on
-- the values in their respective official_* columns.

-- usage enums are set if their value is 10 and the corresponding bool
-- is TRUE.

-- Set error messages per the wiki.
SET client_min_messages=ERROR;

-- Some constants:
-- ServiceUsage.UNKNOWN is 10.
-- ServiceUsage.LAUNCHPAD is 20.
-- See lp.app.enums for more information.

-- Translations
UPDATE Product
    SET translations_usage = 20
    WHERE
        translations_usage = 10 AND
        official_rosetta = True;

-- Answers
UPDATE Product
    SET answers_usage = 20
    WHERE
        answers_usage = 10 AND
        official_answers = True;

-- Blueprints
UPDATE Product
    SET blueprints_usage = 20
    WHERE
        blueprints_usage = 10 AND
        official_blueprints = True;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
