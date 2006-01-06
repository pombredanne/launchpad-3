
set client_min_messages=ERROR;

/* Development Manifests

   This patch creates the table needed to support an ongoing "development
   manifest" for a source package. Essentially this is a "HEAD" of
   development, it represents the last version of the manifest which this
   person is working on.
*/

CREATE TABLE DevelopmentManifest (
  id                serial PRIMARY KEY,
  owner             integer NOT NULL CONSTRAINT
                            developmentmanifest_owner_fk
                            REFERENCES Person(id),
  distrorelease     integer NOT NULL CONSTRAINT
                            developmentmanifest_distrorelease_fk
                            REFERENCES DistroRelease(id),
  sourcepackagename integer NOT NULL CONSTRAINT
                            developmentmanifest_sourcepackagename_fk
                            REFERENCES SourcePackageName(id),
  manifest          integer NOT NULL CONSTRAINT
                            developmentmanifest_manifest_fk
                            REFERENCES Manifest(id),
  datecreated       timestamp WITHOUT TIME ZONE DEFAULT
                            (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

CREATE INDEX developmentmanifest_manifest_idx
    ON DevelopmentManifest(manifest);

CREATE INDEX developmentmanifest_package_created_idx
    ON DevelopmentManifest(distrorelease, sourcepackagename, datecreated);

CREATE INDEX developmentmanifest_datecreated_idx
    ON DevelopmentManifest(datecreated);

CREATE INDEX developmentmanifest_owner_datecreated_idx
    ON DevelopmentManifest(owner, datecreated);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,26,0);

