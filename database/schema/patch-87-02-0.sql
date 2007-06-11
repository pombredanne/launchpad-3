SET client_min_messages=ERROR;

ALTER TABLE ProductReleaseFile ADD COLUMN description TEXT;

-- Add the new column for uploader.
ALTER TABLE ProductReleaseFile
    ADD COLUMN uploader integer;
-- Add the new colum for date_uploaded
ALTER TABLE ProductReleaseFile
    ADD COLUMN date_uploaded timestamp without time zone;

-- Set the uploader value to that of the ProductRelease owner for
-- existing rows.
-- Set the date_uploaded value to that of the ProductRelease
-- datecreated for existing rows.
UPDATE ProductReleaseFile
SET date_uploaded=datecreated, uploader=owner
FROM ProductRelease
WHERE ProductReleaseFile.productrelease=ProductRelease.id;

-- All references to Person need an index for people merge
CREATE INDEX productreleasefile__uploader__idx
    ON ProductReleaseFile(uploader);

-- Now we can set the column to be NOT NULL.
ALTER TABLE ProductReleaseFile ALTER COLUMN uploader
    SET NOT NULL;

-- Add the foreign key constraint
ALTER TABLE ProductReleaseFile
    ADD CONSTRAINT productreleasefile__uploader__fk
        FOREIGN KEY (uploader) REFERENCES person(id);

-- Now set a default to be the current time when the row is created
-- and NOT NULL.
ALTER TABLE ProductReleaseFile ALTER COLUMN date_uploaded
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

ALTER TABLE ProductReleaseFile ALTER COLUMN date_uploaded
    SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 2, 0);
