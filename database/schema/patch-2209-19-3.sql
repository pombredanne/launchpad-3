-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

DROP VIEW combinedbugsummary;
CREATE OR REPLACE VIEW combinedbugsummary AS
    SELECT
        bugsummary.id, bugsummary.count, bugsummary.product,
        bugsummary.productseries, bugsummary.distribution,
        bugsummary.distroseries, bugsummary.sourcepackagename,
        bugsummary.viewed_by, bugsummary.tag, bugsummary.status,
        bugsummary.milestone, bugsummary.importance, bugsummary.has_patch,
        bugsummary.fixed_upstream, bugsummary.access_policy
    FROM bugsummary
    UNION ALL 
    SELECT
        -bugsummaryjournal.id AS id, bugsummaryjournal.count,
        bugsummaryjournal.product, bugsummaryjournal.productseries,
        bugsummaryjournal.distribution, bugsummaryjournal.distroseries,
        bugsummaryjournal.sourcepackagename, bugsummaryjournal.viewed_by,
        bugsummaryjournal.tag, bugsummaryjournal.status,
        bugsummaryjournal.milestone, bugsummaryjournal.importance,
        bugsummaryjournal.has_patch, bugsummaryjournal.fixed_upstream,
        bugsummaryjournal.access_policy
    FROM bugsummaryjournal;

DROP INDEX bugsummary__distribution__unique;
DROP INDEX bugsummary__distroseries__unique;
DROP INDEX bugsummary__product__unique;
DROP INDEX bugsummary__productseries__unique;
DROP INDEX bugsummary__distribution__idx;
DROP INDEX bugsummary__distroseries__idx;
DROP INDEX bugsummary__full__idx;
DROP INDEX bugsummary__distribution_count__idx;
DROP INDEX bugsummary__distribution_tag_count__idx;
DROP INDEX bugsummary__tag_count__idx;
ALTER INDEX bugsummary__distribution__idx2 RENAME TO bugsummary__distribution__idx;
ALTER INDEX bugsummary__distroseries__idx2 RENAME TO bugsummary__distroseries__idx;
ALTER INDEX bugsummary__distribution_count__idx2 RENAME TO bugsummary__distribution_count__idx;
ALTER INDEX bugsummary__distroseries_count__idx2 RENAME TO bugsummary__distroseries_count__idx;
ALTER INDEX bugsummary__distribution_tag_count__idx2 RENAME TO bugsummary__distribution_tag_count__idx;
ALTER INDEX bugsummary__distroseries_tag_count__idx2 RENAME TO bugsummary__distroseries_tag_count__idx;
ALTER INDEX bugsummary__full__idx2 RENAME TO bugsummary__full__idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 19, 3);
