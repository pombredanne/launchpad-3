SET client_min_messages=ERROR;

-- Migrate any POFile.path with NULL value

CREATE OR REPLACE FUNCTION dirname(path text) RETURNS text AS
$$
import os.path
return os.path.dirname(args[0])
$$ LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT;

UPDATE POFile
SET path=(SELECT dirname(POTemplate.path)) || '/' || language.code || COALESCE('@' || variant, '') || '.po'
FROM Language, POTemplate
WHERE POFile.language = Language.id AND POFile.potemplate = POTemplate.id AND POFile.path IS NULL;

DROP FUNCTION dirname(text);

-- And now, we add the DB constraints.

ALTER TABLE POFile ALTER COLUMN path SET NOT NULL;

ALTER TABLE POTemplate ALTER COLUMN path SET NOT NULL;

-- This restriction is not valid anymore.

ALTER TABLE TranslationImportQueueEntry DROP CONSTRAINT valid_upload;

ALTER TABLE POFile DROP CONSTRAINT pofile_rawimportstatus_valid;


-- Add the new field to know the status of every entry on the queue.

ALTER TABLE TranslationImportQueueEntry ADD COLUMN status integer;
ALTER TABLE TranslationImportQueueEntry ALTER COLUMN status SET DEFAULT 5;
-- Add a new field to track status changes.

ALTER TABLE TranslationImportQueueEntry ADD COLUMN date_status_changed timestamp without time zone;

ALTER TABLE TranslationImportQueueEntry ALTER COLUMN date_status_changed SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');


-- By default all entries need to be reviewed.
-- By default all entries have the status change set at the time they were imported.

UPDATE TranslationImportQueueEntry SET status=5, date_status_changed=dateimported WHERE is_blocked = FALSE;

UPDATE TranslationImportQueueEntry SET status=6, date_status_changed=dateimported WHERE is_blocked = TRUE;


-- Now is safe to set the field as NOT NULL.

ALTER TABLE TranslationImportQueueEntry ALTER COLUMN status SET NOT NULL;

ALTER TABLE TranslationImportQueueEntry ALTER COLUMN date_status_changed SET NOT NULL;


-- Generate a table of POFile entries to import into the queue.
-- We can't import all of them, as that would create duplicates
CREATE TEMPORARY TABLE InterestingPOFiles (id int UNIQUE)
ON COMMIT DROP;
INSERT INTO InterestingPOFiles
    SELECT id FROM (
        SELECT
            MAX(POFile.id) AS id, POFile.rawimporter, POFile.path,
            distrorelease, sourcepackagename, productseries
        FROM POFile, POTemplate
        WHERE
            POFile.potemplate = POTemplate.id
            AND POFile.rawfile IS NOT NULL
            AND POFile.rawimportstatus IN (2,4)
            AND NOT EXISTS (
                SELECT * FROM TranslationImportQueueEntry AS tq
                WHERE POFile.path = tq.path AND POFile.rawimporter = tq.importer
                    AND coalesce(POTemplate.distrorelease,-1) = coalesce(tq.distrorelease, -1)
                    AND coalesce(POTemplate.sourcepackagename,-1) = coalesce(tq.sourcepackagename, -1)
                    AND coalesce(POTemplate.productseries,-1) = coalesce(tq.productseries, -1)
                )
        GROUP BY
            POFile.rawimporter, POFile.path,
            distrorelease,sourcepackagename,productseries
        ) AS whatever;

INSERT INTO TranslationImportQueueEntry (path, content, importer,
    dateimported, is_blocked, is_published, distrorelease,
    sourcepackagename, productseries, pofile, potemplate, status,
    date_status_changed)
    SELECT
        POFile.path,
        POFile.rawfile,
        POFile.rawimporter,
        POFile.daterawimport,
        False,
        POFile.rawfilepublished,
        POTemplate.distrorelease,
        POTemplate.sourcepackagename,
        POTemplate.productseries,
        POFile.id,
        POTemplate.id,
        CASE POFile.rawimportstatus WHEN 2 THEN 1 WHEN 4 THEN 4 END,
        POFile.daterawimport
    FROM InterestingPOFiles, POFile, POTemplate
    WHERE
        InterestingPOFiles.id = POFile.id
        AND POFile.potemplate = POTemplate.id;

-- Generate a table of POFile entries to import into the queue.
-- We can't import all of them, as that would create duplicates
CREATE TEMPORARY TABLE InterestingPOTemplates (id int UNIQUE)
ON COMMIT DROP;
INSERT INTO InterestingPOTemplates
    SELECT id FROM (
        SELECT
            MAX(id) AS id, rawimporter, path,
            distrorelease, sourcepackagename, productseries
        FROM POTemplate
        WHERE
            rawfile IS NOT NULL AND rawimportstatus IN (2,4)
            AND NOT EXISTS (
                SELECT * FROM TranslationImportQueueEntry AS tq
                WHERE POTemplate.path = tq.path AND POTemplate.rawimporter = tq.importer
                    AND coalesce(POTemplate.distrorelease,-1) = coalesce(tq.distrorelease, -1)
                    AND coalesce(POTemplate.sourcepackagename,-1) = coalesce(tq.sourcepackagename, -1)
                    AND coalesce(POTemplate.productseries,-1) = coalesce(tq.productseries, -1)
                )
        GROUP BY
            rawimporter, path,
            distrorelease,sourcepackagename,productseries
        ) AS whatever;


INSERT INTO TranslationImportQueueEntry (
    path, content, importer, dateimported, is_blocked, is_published,
    distrorelease, sourcepackagename, productseries, potemplate,
    status, date_status_changed)
    SELECT
        POTemplate.path,
        POTemplate.rawfile,
        POTemplate.rawimporter,
        POTemplate.daterawimport,
        FALSE,
        TRUE,
        POTemplate.distrorelease,
        POTemplate.sourcepackagename,
        POTemplate.productseries,
        POTemplate.id,
        CASE POTemplate.rawimportstatus WHEN 2 THEN 1 WHEN 4 THEN 4 END,
        POTemplate.daterawimport
    FROM POTemplate,InterestingPOTemplates
    WHERE POTemplate.id = InterestingPOTemplates.id;

-- Remove old fields we are not using anymore...

ALTER TABLE TranslationImportQueueEntry DROP COLUMN is_blocked;

ALTER TABLE POFile DROP COLUMN rawimporter;

ALTER TABLE POFile DROP COLUMN daterawimport;

ALTER TABLE POFile DROP COLUMN rawimportstatus;

ALTER TABLE POFile DROP COLUMN rawfile;

ALTER TABLE POFile DROP COLUMN rawfilepublished;

ALTER TABLE POTemplate DROP COLUMN rawimporter;

ALTER TABLE POTemplate DROP COLUMN daterawimport;

ALTER TABLE POTemplate DROP COLUMN rawimportstatus;

ALTER TABLE POTemplate DROP COLUMN rawfile;


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 28, 0);

