-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE branch
    DROP COLUMN merge_queue,
    DROP COLUMN merge_queue_config;

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

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 67, 0);
