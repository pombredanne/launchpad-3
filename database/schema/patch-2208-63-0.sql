-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE bugsummary(
count INTEGER NOT NULL default 0,
product INTEGER REFERENCES Product ON DELETE CASCADE,
productseries INTEGER REFERENCES ProductSeries ON DELETE CASCADE,
distribution INTEGER REFERENCES Distribution ON DELETE CASCADE,
distroseries INTEGER REFERENCES DistroSeries ON DELETE CASCADE,
sourcepackagename INTEGER REFERENCES SourcePackageName ON DELETE CASCADE,
viewed_by INTEGER REFERENCES Person ON DELETE CASCADE,
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
INSERT INTO bugsummary WITH
-- kill dupes
relevant_bug AS (SELECT * FROM bug where duplicateof is NULL),
-- (bug.id, tag) for all bug-tag pairs plus (bug.id, NULL) for all bugs
bug_tags AS (
    (SELECT relevant_bug.id, NULL::text AS tag FROM relevant_bug)
    UNION
    (SELECT relevant_bug.id, tag FROM relevant_bug INNER JOIN bugtag ON relevant_bug.id=bugtag.bug)),
-- (bug.id, NULL) for all public bugs + (bug.id, viewer) for all (subscribers+assignee) on private bugs
bug_viewers AS (
    (SELECT relevant_bug.id, NULL::integer AS person FROM relevant_bug WHERE NOT relevant_bug.private)
    UNION
    (SELECT relevant_bug.id, assignee AS person FROM relevant_bug INNER JOIN bugtask ON relevant_bug.id=bugtask.bug WHERE relevant_bug.private and bugtask.assignee IS NOT NULL)
    UNION
    (SELECT relevant_bug.id, bugsubscription.person FROM relevant_bug INNER JOIN bugsubscription ON bugsubscription.bug=relevant_bug.id WHERE relevant_bug.private)),
-- (bugtask.(bug, product, productseries, distribution, distroseries, sourcepackagename, status, milestone) for all bugs + the same with sourcepackage squashed to NULL)
tasks AS (
    (SELECT bug, product, productseries, distribution, distroseries, sourcepackagename, status, milestone FROM bugtask)
    UNION
    (SELECT DISTINCT ON (bug, product, productseries, distribution, distroseries, sourcepackagename, milestone) bug, product, productseries, distribution, distroseries, NULL::integer as sourcepackagename, status, milestone FROM bugtask where sourcepackagename IS NOT NULL))
-- Now combine
SELECT count(*), product, productseries, distribution, distroseries, sourcepackagename, person, tag, status, milestone FROM relevant_bug INNER JOIN bug_tags ON relevant_bug.id=bug_tags.id INNER JOIN bug_viewers ON relevant_bug.id=bug_viewers.id INNER JOIN tasks on tasks.bug=relevant_bug.id
GROUP BY product, productseries, distribution, distroseries, sourcepackagename, person, tag, status, milestone;

-- Need indices for FK CASCADE DELETE to find any FK easily
CREATE INDEX bugsummary_distribution on bugsummary using btree(distribution);
CREATE INDEX bugsummary_distroseries on bugsummary using btree(distroseries);
CREATE INDEX bugsummary_privates on bugsummary using btree(viewed_by) where viewed_by is not null;
CREATE INDEX bugsummary_product on bugsummary using btree(product);
CREATE INDEX bugsummary_productseries on bugsummary using btree(productseries);
-- can only have one fact row per set of dimensions
CREATE UNIQUE INDEX bugsummary_dimensions_unique_idx ON bugsummary USING btree (
    COALESCE(product, (-1)),
    COALESCE(productseries, (-1)),
    COALESCE(distribution, (-1)),
    COALESCE(distroseries, (-1)),
    COALESCE(sourcepackagename, (-1)),
    COALESCE(viewed_by, (-1)),
    COALESCE(tag, ('')),
    status,
    COALESCE(milestone, (-1)));
-- While querying is tolerably fast with the base dimension indices, we want snappy:
-- Distribution bug counts
CREATE INDEX bugsummary_distribution_count_idx on bugsummary using btree(distribution) where sourcepackagename is null and tag is null;
-- Distribution wide tag counts
CREATE INDEX bugsummary_distribution_tag_count_idx on bugsummary using btree(distribution) where sourcepackagename is null and tag is not null;
-- Everything (counts)
CREATE INDEX bugsummary_count_idx on bugsummary using btree(status) where sourcepackagename is null and tag is null;
-- Everything (tags)
CREATE INDEX bugsummary_tag_count_idx on bugsummary using btree(status) where sourcepackagename is null and tag is not null;

-- we need to maintain the summaries when things change. Each variable the
-- population script above uses needs to be accounted for.

-- bug: duplicateof, private (not INSERT because a task is needed to be included in summaries.
CREATE TRIGGER bug_maintain_bug_summary_trigger AFTER UPDATE OR DELETE ON bug FOR EACH ROW EXECUTE PROCEDURE bug_maintain_bug_summary();
-- bugtask: target, status, milestone
CREATE TRIGGER bugtask_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugtask FOR EACH ROW EXECUTE PROCEDURE bugtask_maintain_bug_summary();
-- bugsubscription: existence
CREATE TRIGGER bugsubscription_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugsubscription FOR EACH ROW EXECUTE PROCEDURE bugsubscription_maintain_bug_summary();
-- bugtag: existence
CREATE TRIGGER bugtag_maintain_bug_summary_trigger AFTER INSERT OR UPDATE OR DELETE ON bugtag FOR EACH ROW EXECUTE PROCEDURE bugtag_maintain_bug_summary();

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 63, 0);
