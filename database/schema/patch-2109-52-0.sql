SET client_min_messages=ERROR;

CREATE TABLE RevisionCache (
    id serial PRIMARY KEY,
    revision integer NOT NULL
        CONSTRAINT revisioncache__revision__fk
        REFERENCES Revision,
    revision_author integer NOT NULL
        CONSTRAINT revisioncache__revision_author__fk
        REFERENCES RevisionAuthor,
    revision_date timestamp without time zone NOT NULL,
    product integer
        CONSTRAINT revisioncache__product__fk
        REFERENCES Product,
    distroseries integer
        CONSTRAINT revisioncache__distroseries__fk
        REFERENCES Distroseries,
    sourcepackagename integer
        CONSTRAINT revisioncache__sourcepackagename__fk
        REFERENCES SourcePackageName,
    private boolean NOT NULL,
    CONSTRAINT valid_target
        CHECK (
            (distroseries IS NULL = sourcepackagename IS NULL)
            AND (
                (distroseries IS NULL AND product IS NULL)
                OR (distroseries IS NULL <> product IS NULL))));

-- Populate RevisionCache with some initial data. We use a hardcoded
-- date as we can't use CURRENT_TIMESTAMP, as this would be
-- non-deterministic and break replication.
INSERT INTO RevisionCache (
    revision, revision_author, revision_date, product, distroseries,
    sourcepackagename, private)
SELECT DISTINCT
    Revision.id, Revision.revision_author, Revision.revision_date,
    Branch.product, Branch.distroseries, Branch.sourcepackagename,
    Branch.private
FROM Revision
JOIN BranchRevision ON BranchRevision.revision = Revision.id
JOIN Branch ON Branch.id = BranchRevision.branch
WHERE
    Revision.revision_date > '2009-03-20'
ORDER BY
    Revision.id, Branch.product, Branch.distroseries, Branch.sourcepackagename;


CREATE UNIQUE INDEX revisioncache__product__revision__key
    ON RevisionCache(product, revision) WHERE product IS NOT NULL;

CREATE UNIQUE INDEX
    revisioncache__distroseries__sourcepackagename__revision__key
    ON RevisionCache(distroseries, sourcepackagename, revision)
    WHERE distroseries IS NOT NULL;

-- we will be deleting rows like
--   "delete revisioncache where revision_date < 'now - 30 days'"
CREATE INDEX revisioncache__revision_date__idx ON RevisionCache(revision_date);

CREATE INDEX revisioncache__revision__idx ON RevisionCache(revision);
CREATE INDEX revisioncache__revision_author__idx
    ON RevisionCache(revision_author);

/*
If we only ever keep 30 days of info, then we should be able to do the
following queries:

== Revisions added across launchpad ==

SELECT COUNT(DISTINCT(revision)) from RevisionCache;

== Distinct revision authors across all branches ==

SELECT COUNT(DISTINCT(COALESCE(ra.person, -ra.id)))
FROM RevisionCache rc, RevisionAuthor ra
WHERE rc.revision_author = ra.id

== Revisions added for the Launchpad project ==

SELECT COUNT(revision) from RevisionCache
WHERE product = x;

-- distinct not needed as it should be unique for a product

== Distinct revision authors across a project ==

SELECT COUNT(DISTINCT(COALESCE(ra.person, -ra.id)))
FROM RevisionCache rc, RevisionAuthor ra
WHERE rc.revision_author = ra.id
AND rc.product = x;

== Revisions added for the Launchpad project-group ==

SELECT COUNT(DISTINCT(revision)) from RevisionCache
JOIN Product ON RevisionCache.product = Product.id
WHERE Product.project = x;

== Distinct revision authors across a project-group ==

SELECT COUNT(DISTINCT(COALESCE(ra.person, -ra.id)))
FROM RevisionCache rc
JOIN RevisionAuthor ra ON rc.revision_author = ra.id
JOIN Product ON rc.product = Product.id
WHERE Product.project = x;

== Revisions added by a Person/Team ==

SELECT COUNT(DISTINCT(revision))
FROM RevisionCache rc
JOIN RevisionAuthor ra ON rc.revision_author = ra.id
JOIN TeamParticipation tp ON tp.person = ra.person
WHERE tp.team = x;


== Revisions authors for a team ==

SELECT COUNT(DISTINCT(ra.person))
FROM RevisionCache rc
JOIN RevisionAuthor ra ON rc.revision_author = ra.id
JOIN TeamParticipation tp ON tp.person = ra.person
WHERE tp.team = x;


There are a few other combinations, like revisions by a team in a project or
project group, but you get the idea.
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 52, 0);
