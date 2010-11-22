-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN file_bug_duplicate_search BOOLEAN NOT NULL DEFAULT True;
ALTER TABLE DistributionSourcePackage
    ADD COLUMN file_bug_duplicate_search BOOLEAN NOT NULL DEFAULT True;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
