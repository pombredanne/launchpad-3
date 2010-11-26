SET client_min_messages=ERROR;

ALTER TABLE SourcePackagePublishingHistory
    ADD COLUMN ancestor INTEGER REFERENCES SourcePackagePublishingHistory;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

