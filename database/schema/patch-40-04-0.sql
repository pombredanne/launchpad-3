-- Quieten things down...
SET client_min_messages=ERROR;

CREATE TABLE TranslationImportQueue(
  id                serial NOT NULL PRIMARY KEY,
  path              text NOT NULL,
  content           integer REFERENCES LibraryFileAlias(id) NOT NULL,
  importer          integer NOT NULL REFERENCES Person(id),
  dateimported      timestamp without time zone NOT NULL DEFAULT
                               (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  distrorelease     integer REFERENCES DistroRelease(id),
  sourcepackagename integer REFERENCES SourcePackageName(id),
  productseries     integer REFERENCES ProductSeries(id),
  blocked           boolean NOT NULL DEFAULT FALSE,
  is_published       boolean NOT NULL,
  pofile            integer REFERENCES POFile(id),
  potemplate        integer REFERENCES POTemplate(id),
  CONSTRAINT        valid_link CHECK (
                 ((productseries IS NULL) <> (distrorelease IS NULL)) AND
                  ((distrorelease IS NULL) = (sourcepackagename IS NULL))),
  CONSTRAINT        valid_upload CHECK (
                 ((pofile IS NULL) AND (potemplate IS NULL)) OR
                 ((pofile IS NULL) <> (potemplate IS NULL)))
);

CREATE UNIQUE INDEX unique_entry_per_importer ON TranslationImportQueue (
                        importer,
                        path,
                        (COALESCE(distrorelease, -1)),
                        (COALESCE(sourcepackagename, -1)),
                        (COALESCE(productseries, -1))
                        );


-- This new field will help us to automatically import POTemplates from
-- one sourcepackage into another sourcepackage. It's main useage is for
-- KDE official packages.
ALTER TABLE POTemplate ADD COLUMN from_sourcepackagename integer REFERENCES SourcePackageName(id);
ALTER TABLE POTemplate ADD CONSTRAINT valid_from_sourcepackagename CHECK (sourcepackagename IS NOT NULL OR from_sourcepackagename IS NULL);

-- join path and filename, then drop filename column
UPDATE POTemplate SET path=REPLACE(path || '/' || filename, '//', '/') WHERE filename IS NOT NULL;
ALTER TABLE POTemplate DROP COLUMN filename;

ALTER TABLE POFile ADD COLUMN from_sourcepackagename integer REFERENCES SourcePackageName(id);
ALTER TABLE POFile RENAME COLUMN filename TO path;

INSERT INTO LaunchpadDatabaseRevision VALUES (40,04,0);
