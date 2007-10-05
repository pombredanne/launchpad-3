SET client_min_messages=ERROR;

CREATE INDEX karmacache_top_in_category_idx
  ON KarmaCache(person,category,karmavalue)
WHERE
  product IS NULL AND
  project  IS NULL AND
  sourcepackagename IS NULL AND
  distribution IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 20, 0);
