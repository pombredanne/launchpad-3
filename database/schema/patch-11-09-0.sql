SET client_min_messages=ERROR;

ALTER TABLE POTemplate ADD binarypackagename integer CONSTRAINT potemplate_binarypackagename_fk REFERENCES BinaryPackageName(id);
ALTER TABLE POTemplate ADD languagepack boolean;
UPDATE POTemplate SET languagepack=FALSE;
ALTER TABLE POTemplate ALTER COLUMN languagepack SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN languagepack SET DEFAULT FALSE;
ALTER TABLE POTemplate ADD filename text;

-- Carlos - reordering this UNIQUE so the index it creates is more useful
-- to the query engine.
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_sourcepackagename_key
    UNIQUE(sourcepackagename, path, filename, distrorelease);

INSERT INTO LaunchpadDatabaseRevision VALUES (11,9,0);
