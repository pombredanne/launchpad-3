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

