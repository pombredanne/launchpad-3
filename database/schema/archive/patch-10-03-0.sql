SET client_min_messages=ERROR;

/* Just like SourcePackagePublishing */
ALTER TABLE PackagePublishing 
    ADD COLUMN datepublished timestamp without time zone;

INSERT INTO LaunchpadDatabaseRevision VALUES (10, 3, 0);
