SET client_min_messages=ERROR;

-- Add the new column for description.
ALTER TABLE ProductReleaseFile ADD COLUMN description TEXT;

-- Add the new column for uploader.
ALTER TABLE ProductReleaseFile
    ADD COLUMN uploader int4;

-- Set the uploader value to that of the ProductRelease owner for existing rows.
UPDATE ProductReleaseFile
SET uploader=(SELECT owner FROM ProductRelease WHERE ProductRelease.id = ProductReleaseFile.productrelease);

-- Now we can set the column to be NOT NULL.
ALTER TABLE ProductReleaseFile ALTER COLUMN uploader
    SET NOT NULL;

-- Add the foreign key constraint
ALTER TABLE ProductReleaseFile
    ADD CONSTRAINT productreleasefile__uploader__fk
        FOREIGN KEY (uploader) REFERENCES person(id);

-- Add the new column for dateuploaded.
ALTER TABLE ProductReleaseFile
    ADD COLUMN dateuploaded timestamp without time zone;
-- Set the dateuploaded value to that of the ProductRelease datecreated for existing rows.
UPDATE ProductReleaseFile
SET dateuploaded=(SELECT datecreated FROM ProductRelease
                         WHERE ProductRelease.id = ProductReleaseFile.productrelease);

-- Now set a default to be the current time when the row is created and NOT NULL.
ALTER TABLE ProductReleaseFile ALTER COLUMN dateuploaded
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE ProductReleaseFile ALTER COLUMN dateuploaded
    SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES(79, 99, 0);
