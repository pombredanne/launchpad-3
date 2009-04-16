SET client_min_messages=ERROR;

CREATE TABLE RevisionCache
(
  id                SERIAL PRIMARY KEY,
  revision          INT References Revision,
  revision_author   INT References RevisionAuthor,
  revision_date     TIMESTAMP WITHOUT TIME ZONE,
  product           INT References Product,
  distroseries      INT References Distroseries,
  sourcepackagename INT References SourcePackageName,
  private           BOOL NOT NULL
);

-- (revision, product) should be unique if product is not NULL
-- (revision, distroseries, sourcepackagename) should be unique if distroseries and sourcepackagename are not NULL
-- if distroseries is NULL, sourcepackagename has to be NULL too, and the same for not null
-- only one of product and (distroseries, sourcepackagename) can have values
-- it is possible for product, distroseries and sourcepackagename to all be NULL
-- we will be deleting rows like
--   "delete revisioncache where revision_date < 'now - 30 days'"

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

INSERT INTO LaunchpadDatabaseRevision
VALUES (2109, 89, 0);
