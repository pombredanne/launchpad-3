SET client_min_messages=ERROR;

-- Canonicalize POFile paths that clash with other POFile paths in the same
-- translation context (either productseries or distroseries/sourcepackage).
CREATE OR REPLACE FUNCTION dirname(path text) RETURNS text AS
$$
import os.path
return os.path.dirname(args[0])
$$ LANGUAGE plpythonu IMMUTABLE RETURNS NULL ON NULL INPUT;

UPDATE POFile AS pf
SET
  path=(SELECT dirname(pt.path)) || '/' ||
       (SELECT pt.name) || '-' || language.code ||
       COALESCE('@' || pf.variant, '') || '.po'
FROM
  Language, POTemplate pt
WHERE
  pf.language = Language.id AND
  pf.potemplate = pt.id AND
  pf.id IN (
    SELECT DISTINCT pf1.id
    FROM POFile pf1
    JOIN POTemplate AS pt1 ON pf1.potemplate = pt1.id
    JOIN POFile AS pf2 ON pf1.path = pf2.path
    JOIN POTemplate AS pt2 ON pf2.potemplate = pt2.id
    WHERE
      pf1.id <> pf2.id AND
      (pt2.productseries = pt1.productseries OR
       (pt2.distroseries = pt1.distroseries AND
        pt2.sourcepackagename = pt1.sourcepackagename))
    );

DROP FUNCTION dirname(text);

-- For a given template, no two translation files should have the same path.
-- This constraint doesn't express the full restriction (paths should also be
-- unique across templates in the same translation context) but it covers one
-- easily-detected case.
CREATE UNIQUE INDEX pofile__potemplate__path__key
    ON POFile(potemplate, path);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);

