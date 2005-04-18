SET client_min_messages=ERROR;

/* SourceSource
   This will go away further down in the script, but it's useful to get it
   cleaned up a big before we remove it altogether.  We add a proper
   ImportStatus, and autotested becomes a datetime
*/

ALTER TABLE SourceSource ADD COLUMN importstatus integer;
UPDATE SourceSource SET importstatus=2 WHERE 
            processingapproved IS NULL AND
            syncingapproved IS NULL AND
            autotested = 0; -- TESTING
UPDATE SourceSource SET importstatus=3 WHERE
            processingapproved IS NULL AND
            syncingapproved IS NULL AND
            autotested = 1;-- TESTFAILED
UPDATE SourceSource SET importstatus=4 WHERE
            processingapproved IS NULL AND
            syncingapproved IS NULL AND
            autotested = 2;-- AUTOTESTED
UPDATE SourceSource SET importstatus=5 WHERE
            processingapproved IS NOT NULL AND
            syncingapproved IS NULL; -- PROCESSING
UPDATE SourceSource SET importstatus=6 WHERE
            processingapproved IS NOT NULL AND
            syncingapproved IS NOT NULL; -- SYNCING
/* this should cover all the SourceSources in the system at present since
 * there is no mechanism to get them into the STOPPED state yet. ERROR if
 * any are left with a NULL importstatus
*/
ALTER TABLE SourceSource ALTER COLUMN importstatus SET NOT NULL;
/* now sort out the autotested column */
ALTER TABLE SourceSource ADD COLUMN dateautotested timestamp without time
zone;
UPDATE SourceSource SET dateautotested=CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE autotested=2;
ALTER TABLE SourceSource DROP COLUMN autotested;
ALTER TABLE SourceSource ADD COLUMN bkrepository text;
/* since sourcesource is now uniquely connected to a productseries, we want
 * the name, title and description to be on the productseries. in due course
 * we will drop these columns but for the moment i'm going to make them just
 * not null */
ALTER TABLE SourceSource ALTER COLUMN name DROP NOT NULL;
ALTER TABLE SourceSource ALTER COLUMN title DROP NOT NULL;
ALTER TABLE SourceSource ALTER COLUMN description DROP NOT NULL;


/* ProductSeries
   We move most of SourceSource into ProductSeries
*/

ALTER TABLE ProductSeries ADD COLUMN branch integer
    CONSTRAINT productseries_branch_fk REFERENCES Branch
    CONSTRAINT productseries_branch_key UNIQUE;
ALTER TABLE ProductSeries ADD COLUMN importstatus integer;
ALTER TABLE ProductSeries ADD COLUMN datelastsynced timestamp without time
zone;
ALTER TABLE ProductSeries ADD COLUMN syncinterval interval;
ALTER TABLE ProductSeries ADD COLUMN rcstype integer;
ALTER TABLE ProductSeries ADD COLUMN cvsroot text;
ALTER TABLE ProductSeries ADD COLUMN cvsmodule text;
ALTER TABLE ProductSeries ADD COLUMN cvsbranch text;
ALTER TABLE ProductSeries ADD COLUMN cvstarfileurl text;
ALTER TABLE ProductSeries ADD COLUMN svnrepository text;
ALTER TABLE ProductSeries ADD COLUMN bkrepository text;
ALTER TABLE ProductSeries ADD COLUMN releaseroot text;
ALTER TABLE ProductSeries ADD COLUMN releasefileglob text;
ALTER TABLE ProductSeries ADD COLUMN releaseverstyle integer;
ALTER TABLE ProductSeries ADD COLUMN targetarcharchive text;
ALTER TABLE ProductSeries ADD COLUMN targetarchcategory text;
ALTER TABLE ProductSeries ADD COLUMN targetarchbranch text;
ALTER TABLE ProductSeries ADD COLUMN targetarchversion text;
ALTER TABLE ProductSeries ADD COLUMN dateautotested timestamp without time
zone;
ALTER TABLE ProductSeries ADD COLUMN dateprocessapproved timestamp without
time zone;
ALTER TABLE ProductSeries ADD COLUMN datesyncapproved timestamp without time
zone;
ALTER TABLE ProductSeries ADD COLUMN datestarted timestamp without time
zone;
ALTER TABLE ProductSeries ADD COLUMN datefinished timestamp without time
zone;

/* now we can map the sourcesource data straight into its corresponding
 * product series columns
*/

UPDATE ProductSeries
    SET
        branch=SourceSource.branch,
        importstatus=SourceSource.importstatus,
        datelastsynced=SourceSource.lastsynced,
        syncinterval=SourceSource.syncinterval,
        rcstype=SourceSource.rcstype,
        cvsroot=SourceSource.cvsroot,
        cvsmodule=SourceSource.cvsmodule,
        cvsbranch=SourceSource.cvsbranch,
        cvstarfileurl=SourceSource.cvstarfileurl,
        svnrepository=SourceSource.svnrepository,
        bkrepository=SourceSource.bkrepository,
        releaseroot=SourceSource.releaseroot,
        releasefileglob=SourceSource.releasefileglob,
        releaseverstyle=SourceSource.releaseverstyle,
        targetarcharchive=SourceSource.newarchive,
        targetarchcategory=SourceSource.newbranchcategory,
        targetarchbranch=SourceSource.newbranchbranch,
        targetarchversion=SourceSource.newbranchversion,
        dateautotested=SourceSource.dateautotested,
        dateprocessapproved=SourceSource.processingapproved,
        datesyncapproved=SourceSource.syncingapproved,
        datestarted=SourceSource.datestarted,
        datefinished=SourceSource.datefinished
    FROM
        SourceSource
    WHERE SourceSource.productseries=ProductSeries.id;

-- drop SourceSource since we have SourceSourceBackup
DROP TABLE SourceSource;

INSERT INTO LaunchpadDatabaseRevision VALUES (14, 8, 0);
