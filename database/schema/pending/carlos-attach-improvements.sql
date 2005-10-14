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
  CONSTRAINT        UNIQUE (importer, distrorelease, sourcepackagename,
                            productseries)
);

ALTER TABLE POFile RENAME COLUMN filename TO path;

-- We need a join of the path and filename fields before removing that column.
--ALTER TABLE POTemplate DROP COLUMN filename;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,99,0);
