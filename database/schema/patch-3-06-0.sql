SET client_min_messages TO error;

/*
  Add SourceForge and Freshmeat references to both Project and Product.
  We need it on both because SF and FM don't differentiate between projects
  and products.
*/

ALTER TABLE project ADD COLUMN sourceforgeproject TEXT;
ALTER TABLE project ADD COLUMN freshmeatproject TEXT;
ALTER TABLE product ADD COLUMN sourceforgeproject TEXT;
ALTER TABLE product ADD COLUMN freshmeatproject TEXT;


/*
 * The SourcepackagePublishing records need a datepublished
 */

ALTER TABLE SourcepackagePublishing
    ADD COLUMN datepublished timestamp without time zone;

/*
 * The SourcepackagePublishing and PackagePublishing records need a
 * date for expected deletion of the publishing record and associated
 * files (assuming they're unreferenced by other DistroReleases in
 * the distribution
 */

ALTER TABLE SourcepackagePublishing
    ADD COLUMN scheduleddeletiondate timestamp without time zone;
    
ALTER TABLE PackagePublishing
    ADD COLUMN scheduleddeletiondate timestamp without time zone;

/*
 * The 'uploadstatus' column name is crack in SourcepackagePublishing
 */

ALTER TABLE SourcepackagePublishing RENAME COLUMN uploadstatus TO status;

/*
 * And PackagePublishing needs a similar status column
 */

ALTER TABLE PackagePublishing ADD COLUMN status integer;
ALTER TABLE PackagePublishing ALTER COLUMN status SET NOT NULL;


