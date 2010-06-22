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

/* Add DistributionSourcePackage row for each
 * SourcePackagePublishingHistory entry whose archive is primary and
 * whose distroseries is current.
 */
INSERT INTO DistributionSourcePackage (
    distribution,
    sourcepackagename
    )
    SELECT
        ds.distribution,
        sourcepackagename
    FROM SourcePackagePublishingHistory spph
        JOIN Archive ON spph.archive = Archive.id
        JOIN SourcePackageRelease spr ON spph.sourcepackagerelease = spr.id
        JOIN DistroSeries ds ON spph.distroseries = ds.id
    WHERE ds.releasestatus = 4 -- CURRENT
        AND Archive.purpose = 1 -- PRIMARY
    EXCEPT
    SELECT
        distribution,
        sourcepackagename
    FROM DistributionSourcePackage;


/* Update cached bug values in DistributionSourcePackage. */
UPDATE DistributionSourcePackage
SET max_bug_heat = subquery.max_bug_heat,
    total_bug_heat = subquery.total_bug_heat,
    bug_count = subquery.bug_count
FROM (
    SELECT
        MAX(Bug.heat) as max_bug_heat,
        SUM(Bug.heat) as total_bug_heat,
        COUNT(Bug.id) as bug_count,
        distribution as distro,
        sourcepackagename as spn
    FROM Bug
        JOIN BugTask ON BugTask.bug = Bug.id
        JOIN DistributionSourcePackage dsp
            USING(distribution, sourcepackagename)
    GROUP BY distribution, sourcepackagename
    ) AS subquery
WHERE distribution = distro
    AND sourcepackagename = spn;
