SET client_min_messages TO error;

/*
 * The SourcepackagePublishing records need a datepublished
 */

ALTER TABLE SourcepackagePublishing
    ADD COLUMN datepublished timestamp;

/*
 * The SourcepackagePublishing and PackagePublishing records need a
 * date for expected deletion of the publishing record and associated
 * files (assuming they're unreferenced by other DistroReleases in
 * the distribution
 */

ALTER TABLE SourcepackagePublishing
    ADD COLUMN scheduleddeletiondate timestamp;
    
ALTER TABLE PackagePublishing
    ADD COLUMN scheduleddeletiondate timestamp;

/*
 * Provide comments about these new columns 
 * (and PackagePublishing.datepublished)
 */
 
COMMENT ON COLUMN SourcepackagePublishing.datepublished IS 'This column contains the timestamp at which point the SourcepackageRelease progressed from a pending publication to being published in the respective DistroRelease';
COMMENT ON COLUMN SourcepackagePublishing.scheduleddeletiondate IS 'This column is only used when the the publishing record is PendingRemoval. It indicates the earliest time that this record can be removed. When a publishing record is removed, the files it embodies are made candidates for removal from the pool.';

COMMENT ON COLUMN SourcepackagePublishing.datepublished IS 'This column contains the timestamp at which point the Build progressed from a pending publication to being published in the respective DistroRelease';
COMMENT ON COLUMN SourcepackagePublishing.scheduleddeletiondate IS 'This column is only used when the the publishing record is PendingRemoval. It indicates the earliest time that this record can be removed. When a publishing record is removed, the files it embodies are made candidates for removal from the pool.';

/*
 * The 'uploadstatus' column name is crack in SourcepackagePublishing
 */

ALTER TABLE SourcepackagePublishing
    RENAME COLUMN uploadstatus TO status;

/*
 * And PackagePublishing needs a similar status column
 */

ALTER TABLE PackagePublishing
    ADD COLUMN status integer;

ALTER TABLE PackagePublishing
    ALTER COLUMN status SET NOT NULL;

/*
 * Provide comments about the status columns
 */

COMMENT ON COLUMN SourcepackagePublishing.status IS 'This column contains the status of the publishing record. The valid states are described in dbschema.py in PackagePublishingStatus. Example states are "Pending" and "Published"';

COMMENT ON COLUMN PackagePublishing.status IS 'This column contains the status of the publishing record. The valid states are described in dbschema.py in PackagePublishingStatus. Example states are "Pending" and "Published"';

