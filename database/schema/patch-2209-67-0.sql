-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE branch
    DROP COLUMN author,
    DROP COLUMN merge_queue,
    DROP COLUMN merge_queue_config;
ALTER TABLE distribution DROP COLUMN upload_admin;
ALTER TABLE distroarchseries DROP COLUMN supports_virtualized;

DROP TABLE binarypackagereleasecontents;
DROP TABLE binarypackagepath;
DROP TABLE branchmergequeue;
DROP TABLE bugnotificationrecipientarchive;
DROP TABLE mirrorcontent;
DROP TABLE mirrorsourcecontent;
DROP TABLE mirror;
DROP TABLE oauthnonce;
DROP TABLE specificationworkitemchange;
DROP TABLE specificationworkitemstats;
DROP TABLE subunitstream;

SELECT job INTO TEMP temp_mergedirectivejob_jobs FROM mergedirectivejob;
DROP TABLE mergedirectivejob;
DELETE FROM job WHERE id IN (SELECT job FROM temp_mergedirectivejob_jobs);

-- Drop some big indices that we never use.
DROP INDEX binarypackagerelease__fti__idx;
DROP INDEX bug__fti__idx;
DROP INDEX messagechunk__fti__idx;
DROP INDEX message__fti__idx;
DROP INDEX securebinarypackagepublishinghistory_status_idx;

-- __idx was only useful for backfilling the column, so let's get rid of
-- it and rename the generally applicable one.
DROP INDEX sourcepackagepublishinghistory__packageupload__idx;
ALTER INDEX sourcepackagepublishinghistory__packageupload__idx_2
    RENAME TO sourcepackagepublishinghistory__packageupload__idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 67, 0);
