-- Quieten things down...
SET client_min_messages=ERROR;

CREATE TABLE TranslationImportQueue(
  id                serial NOT NULL PRIMARY KEY,
  path              text NOT NULL,
  content           integer REFERENCES LibraryFileAlias(id) NOT NULL,
  importer          integer NOT NULL REFERENCES Person(id),
  dateimport        timestamp without time zone NOT NULL DEFAULT
                               (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  distrorelease     integer REFERENCES DistroRelease(id),
  sourcepackagename integer REFERENCES SourcePackageName(id),
  productseries     integer REFERENCES ProductSeries(id),
  ignore            boolean NOT NULL DEFAULT FALSE,
  ispublished       boolean NOT NULL,
  CONSTRAINT        valid_link CHECK (
                 (((productseries IS NULL) <> (distrorelease IS NULL)) AND
                  ((distrorelease IS NULL) = (sourcepackagename IS NULL)))),
  CONSTRAINT        unique_entry_per_importer UNIQUE (importer, distrorelease,
                        sourcepackagename, productseries, path)
);

ALTER TABLE POFile RENAME COLUMN filename TO path;

-- This new field will help us to automatically import POTemplates from
-- one sourcepackage into another sourcepackage. It's main useage is for
-- KDE official packages.
ALTER TABLE POTemplate ADD COLUMN fromsourcepackagename integer REFERENCES SourcePackageName(id);
ALTER TABLE POTemplate ADD CONSTRAINT valid_fromsourcepackagename CHECK (sourcepackagename IS NOT NULL OR fromsourcepackagename IS NULL);

-- We need a join of the path and filename fields before removing that column.
--ALTER TABLE POTemplate DROP COLUMN filename;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,99,0);
