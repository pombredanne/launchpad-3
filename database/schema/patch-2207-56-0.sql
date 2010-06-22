-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 56, 0);

/*
Existing Schema:

CREATE TABLE distributionsourcepackage (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_reporting_guidelines text,
    max_bug_heat integer
);
*/

ALTER TABLE DistributionSourcePackage ADD COLUMN total_bug_heat INTEGER;
ALTER TABLE DistributionSourcePackage ADD COLUMN bug_count INTEGER;
ALTER TABLE DistributionSourcePackage ADD COLUMN po_message_count INTEGER;
ALTER TABLE DistributionSourcePackage
    ADD COLUMN is_upstream_link_allowed BOOLEAN NOT NULL DEFAULT TRUE;
