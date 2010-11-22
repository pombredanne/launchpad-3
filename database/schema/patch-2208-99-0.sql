-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN disable_bugfiling_duplicate_search
        BOOLEAN NOT NULL DEFAULT False;
ALTER TABLE DistributionSourcePackage
    ADD COLUMN disable_bugfiling_duplicate_search
        BOOLEAN NOT NULL DEFAULT False;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
