-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);

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
    ADD COLUMN section INTEGER NOT NULL REFERENCES section(id);

COMMENT ON COLUMN DistributionSourcePackage.total_bug_heat IS
    'Sum of bug heat matching the package distribution and sourcepackagename';
COMMENT ON COLUMN DistributionSourcePackage.bug_count IS
    'Number of bugs matching the package distribution and sourcepackagename';
COMMENT ON COLUMN DistributionSourcePackage.po_message_count IS
    'Number of translations matching the package distribution and sourcepackagename';
COMMENT ON COLUMN DistributionSourcePackage.section IS
    'Cached section matching the latest SourcePackagePublishingHistory record by distribution and sourcepackagename whose archive purpose is PRIMARY and whose distroseries releasestatus is CURRENT.';
