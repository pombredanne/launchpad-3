SET client_min_messages=ERROR;

-- I didn't check the constraints enough.  We can have the same revision listed
-- for a product twice, once with private true and once with false.  Same for
-- source packages.

DROP INDEX revisioncache__product__revision__key;

CREATE UNIQUE INDEX revisioncache__product__revision__private__key
    ON RevisionCache(product, revision, private) WHERE product IS NOT NULL;

DROP INDEX revisioncache__distroseries__sourcepackagename__revision__key;

CREATE UNIQUE INDEX
    revisioncache__distroseries__sourcepackagename__revision__private__key
    ON RevisionCache(distroseries, sourcepackagename, revision, private)
    WHERE distroseries IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 55, 1);
