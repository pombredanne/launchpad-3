SET client_min_messages=ERROR;

-- Kill dupes
UPDATE ProductSeries SET cvsroot=NULL WHERE cvsroot='';
UPDATE ProductSeries SET cvsmodule=NULL WHERE cvsmodule='';
UPDATE ProductSeries SET cvsbranch=NULL WHERE cvsbranch='';
UPDATE ProductSeries SET cvsroot=NULL,cvsmodule=NULL,cvsbranch=NULL
    WHERE cvsroot IS NULL <> cvsbranch IS NULL
        OR cvsroot IS NULL <> cvsmodule IS NULL;
CREATE SEQUENCE tmp_counter;
UPDATE ProductSeries
    SET cvsroot=cvsroot||'-DUPE'||nextval('tmp_counter')
    WHERE id IN (
        SELECT ps1.id
            FROM ProductSeries AS ps1
            JOIN ProductSeries AS ps2 ON (
                ps1.id <> ps2.id
                AND ps1.cvsroot=ps2.cvsroot AND ps1.cvsmodule=ps2.cvsmodule
                AND ps1.cvsbranch = ps2.cvsbranch AND ps1.cvsroot IS NOT NULL
                AND ps1.cvsmodule IS NOT NULL AND ps2.cvsbranch IS NOT NULL
                )
            JOIN Product AS p1 ON ps1.product=p1.id
            JOIN Product AS p2 ON ps2.product=p2.id
            WHERE p1.name IN ('duplicates', 'unassigned')
            );
DROP SEQUENCE tmp_counter;

UPDATE ProductSeries SET targetarcharchive=NULL WHERE targetarcharchive='';
UPDATE ProductSeries SET targetarchcategory=NULL WHERE targetarchcategory='';
UPDATE ProductSeries SET targetarchbranch=NULL WHERE targetarchbranch='';
UPDATE ProductSeries SET targetarchversion=NULL WHERE targetarchversion='';
UPDATE ProductSeries
    SET targetarcharchive=NULL, targetarchcategory=NULL,
        targetarchbranch=NULL, targetarchversion=NULL
    WHERE
        targetarcharchive IS NULL <> targetarchcategory IS NULL
        OR targetarcharchive IS NULL <> targetarchbranch IS NULL
        OR targetarcharchive IS NULL <> targetarchversion IS NULL;
CREATE SEQUENCE tmp_counter;
UPDATE ProductSeries
    SET targetarcharchive=targetarcharchive||'-DUPE'||nextval('tmp_counter')
    WHERE id IN (
        SELECT ps1.id
            FROM ProductSeries AS ps1
            JOIN ProductSeries AS ps2 ON (
                ps1.id <> ps2.id
                AND ps1.targetarcharchive = ps2.targetarcharchive
                AND ps1.targetarchcategory =ps2.targetarchcategory
                AND ps1.targetarchbranch = ps2.targetarchbranch
                AND ps1.targetarchversion = ps2.targetarchversion
                AND ps1.targetarcharchive IS NOT NULL
                AND ps1.targetarchcategory IS NOT NULL
                AND ps1.targetarchbranch IS NOT NULL
                AND ps1.targetarchversion IS NOT NULL
                )
            JOIN Product AS p1 ON ps1.product=p1.id
            JOIN Product AS p2 ON ps2.product=p2.id
            WHERE p1.name IN ('duplicates', 'unassigned')
            );
DROP SEQUENCE tmp_counter;

UPDATE ProductSeries SET svnrepository=NULL WHERE svnrepository='';
CREATE SEQUENCE tmp_counter;
UPDATE ProductSeries
    SET svnrepository=svnrepository||'-DUPE'||nextval('tmp_counter')
    WHERE id IN (
        SELECT ps1.id
            FROM ProductSeries AS ps1
            JOIN ProductSeries AS ps2 ON (
                ps1.id <> ps2.id
                AND ps1.svnrepository=ps2.svnrepository
                AND ps1.svnrepository IS NOT NULL
                )
            JOIN Product AS p1 ON ps1.product=p1.id
            JOIN Product AS p2 ON ps2.product=p2.id
            WHERE p1.name IN ('duplicates', 'unassigned')
            );
DROP SEQUENCE tmp_counter;

UPDATE ProductSeries SET bkrepository=NULL WHERE bkrepository='';

-- Ensure our branches are unique
ALTER TABLE ProductSeries ADD CONSTRAINT productseries_cvsroot_key
    UNIQUE (cvsroot, cvsmodule, cvsbranch);

ALTER TABLE ProductSeries ADD CONSTRAINT productseries_targetarcharchive_key
    UNIQUE (targetarcharchive, targetarchcategory,
        targetarchbranch, targetarchversion);

ALTER TABLE ProductSeries ADD CONSTRAINT productseries_svnrepository_key
    UNIQUE (svnrepository);

ALTER TABLE ProductSeries ADD CONSTRAINT productseries_bkrepository_key
    UNIQUE (bkrepository);

-- Ensure our branches are complete

ALTER TABLE ProductSeries ADD CONSTRAINT complete_cvs CHECK (
    (cvsroot IS NULL = cvsmodule IS NULL)
    AND (cvsroot IS NULL = cvsbranch IS NULL)
    );

ALTER TABLE ProductSeries ADD CONSTRAINT complete_targetarch CHECK (
    (targetarcharchive IS NULL = targetarchcategory IS NULL)
    AND (targetarcharchive IS NULL = targetarchbranch IS NULL)
    AND (targetarcharchive IS NULL = targetarchversion IS NULL)
    );

-- Ensure our branches don't get any more empty strings in 'em, as this
-- stuffs the UNIQUE constraints
ALTER TABLE ProductSeries ADD CONSTRAINT no_empty_strings CHECK (
    targetarcharchive <> '' AND targetarchcategory <> ''
    AND targetarchbranch <> '' AND targetarchversion <> ''
    AND cvsroot <> '' AND cvsmodule <> '' AND cvsbranch <> ''
    AND svnrepository <> '' AND bkrepository <> ''
    );

INSERT INTO LaunchpadDatabaseRevision VALUES  (17, 2, 0);

