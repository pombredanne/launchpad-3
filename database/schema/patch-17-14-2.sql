set client_min_messages=ERROR;

UPDATE ProductSeries SET importstatus=2
    WHERE importstatus IS NULL AND rcstype IS NOT NULL;

ALTER TABLE ProductSeries ADD CONSTRAINT valid_importseries
    CHECK ( (importstatus IS NULL) OR (rcstype IS NOT NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 14, 2);

