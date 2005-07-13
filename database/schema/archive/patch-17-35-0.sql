
SET client_min_messages=ERROR;

ALTER TABLE POExportRequest ADD COLUMN format integer;

UPDATE POExportRequest SET format=1;
ALTER TABLE POExportRequest ALTER COLUMN format SET NOT NULL;

DROP INDEX poexportrequest_person_key;
CREATE UNIQUE INDEX poexportrequest_duplicate_key
    ON POExportRequest (potemplate, person, format, (COALESCE(pofile, -1)));

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 35, 0);

