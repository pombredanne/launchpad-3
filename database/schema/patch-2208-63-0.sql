-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE bugsummary(
count INTEGER NOT NULL default 0,
product INTEGER REFERENCES Product ON DELETE CASCADE,
productseries INTEGER REFERENCES ProductSeries ON DELETE CASCADE,
distribution INTEGER REFERENCES Distribution ON DELETE CASCADE,
distroseries INTEGER REFERENCES DistroSeries ON DELETE CASCADE,
sourcepackagename INTEGER REFERENCES SourcesPackageName ON DELETE CASCADE,
viewedby INTEGER REFERENCES Person ON DELETE CASCADE,
tag TEXT,
status INTEGER NOT NULL,
milestone INTEGER REFERENCES Milestone ON DELETE CASCADE,
CONSTRAINT bugtask_assignment_checks CHECK (CASE WHEN (product IS NOT NULL) THEN ((((productseries IS NULL) AND (distribution IS NULL)) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL)) WHEN (productseries IS NOT NULL) THEN (((distribution IS NULL) AND (distroseries IS NULL)) AND (sourcepackagename IS NULL)) WHEN (distribution IS NOT NULL) THEN (distroseries IS NULL) WHEN (distroseries IS NOT NULL) THEN true ELSE false END)
);

---- Bulk load into the table - after this it is maintained by trigger. Timed
-- at 2-3 minutes on staging.
-- basic theory: each bug *task* has some unary dimensions (like status) and
-- some N-ary dimensions (like contexts [sourcepackage+distro, distro only], or
-- subscriptions, or tags). For N-ary dimensions we record the bug against all
-- positions in that dimension.
-- Some tasks aggregate into the same dimension - e.g. two different source
-- packages tasks in Ubuntu. At the time of writing we only want to count those
-- once ( because we have had user confusion when two tasks of the same bug are
-- both counted toward portal aggregates). So we add bug.id distinct.
-- We don't map INCOMPLETE to INCOMPLETE_WITH_RESPONSE - instead we'll let that
-- migration happen separately.
-- So the rules the code below should be implementing are:
-- once for each task in a different target
-- once for each subscription (private bugs) (left join subscribers conditionally on privacy)
-- once for each sourcepackage name + one with sourcepackagename=NULL (two queries unioned)
-- once for each tag + one with tag=NULL (two queries unioned)
-- bugs with duplicateof non null are excluded because we exclude them from all our aggregates.
INSERT INTO bugsummary SELECT sum(count), product, productseries, distribution, distroseries, sourcepackagename, person, tag, status, milestone FROM (
-- bugs with tags against the tag=NULL aggregate with sourcepackagename
(SELECT DISTINCT ON (bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone) count(*), product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, NULL::text AS tag, status, milestone FROM bug left join bugsubscription ON (bug.private AND bugsubscription.bug=bug.id), bugtask WHERE bug.id=bugtask.bug AND EXISTS (SELECT true FROM bugtag WHERE bugtag.bug=bug.id) AND duplicateof IS NULL GROUP BY bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone)
UNION ALL
-- bugs with tags against the tag=NULL aggregate, with sourcepackagenames against their distro[series] aggregate
(SELECT DISTINCT ON (bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone) count(*), product, productseries, distribution, distroseries, NULL::integer AS sourcepackagename, bugsubscription.person, NULL::text AS tag, status, milestone FROM bug left join bugsubscription ON (bug.private AND bugsubscription.bug=bug.id), bugtask WHERE bug.id=bugtask.bug AND EXISTS (SELECT true FROM bugtag WHERE bugtag.bug=bug.id) AND duplicateof IS NULL AND sourcepackagename IS NOT NULL GROUP BY bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone)

UNION ALL
-- bugs with tags with sourcepackagename
(SELECT DISTINCT ON (bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone) count(*), product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, tag, status, milestone FROM bug left join bugtag ON bugtag.bug=bug.id left join bugsubscription ON (bug.private AND bugsubscription.bug=bug.id), bugtask WHERE bug.id=bugtask.bug AND duplicateof IS NULL GROUP BY bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, tag, status, milestone)
UNION ALL
-- bugs with tags for distro[series] level aggregation (sourcepackagename clamped to NULL, once per bug))
(SELECT DISTINCT ON (bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, status, milestone) count(*), product, productseries, distribution, distroseries, NULL::integer AS sourcepackagename, bugsubscription.person, tag, status, milestone FROM bug left join bugtag ON bugtag.bug=bug.id left join bugsubscription ON (bug.private AND bugsubscription.bug=bug.id), bugtask WHERE bug.id=bugtask.bug AND duplicateof IS NULL AND sourcepackagename IS NOT NULL GROUP BY bug.id, product, productseries, distribution, distroseries, sourcepackagename, bugsubscription.person, tag, status, milestone)

) AS _tmp
GROUP BY product, productseries, distribution, distroseries, sourcepackagename, person, tag, status, milestone;


CREATE INDEX bugsummary_distribution on bugsummary using btree(distribution);
CREATE INDEX bugsummary_distroseries on bugsummary using btree(distroseries);
CREATE INDEX bugsummary_privates on bugsummary using btree(viewedby) where viewedby is not null;
CREATE INDEX bugsummary_product on bugsummary using btree(product);
CREATE INDEX bugsummary_productseries on bugsummary using btree(productseries);
-- can only have one fact row per set of dimensions
CREATE UNIQUE INDEX bugsummary_dimensions_unique_idx ON bugsummary USING btree (
    COALESCE(product, (-1)),
    COALESCE(productseries, (-1)),
    COALESCE(distribution, (-1)),
    COALESCE(distroseries, (-1)),
    COALESCE(sourcepackagename, (-1)),
    COALESCE(viewedby, (-1)),
    COALESCE(tag, ('')),
    status,
    COALESCE(milestone, (-1)));

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 0);

