SET client_min_messages=ERROR;

-- Per Bug #196774
ALTER TABLE Packaging
    DROP CONSTRAINT packaging_uniqueness,
    ADD CONSTRAINT packaging_uniqueness
        UNIQUE (distroseries, sourcepackagename);

INSERT INTO LaunchpadDatabaseRevision VALUES (2297, 0, 0);

