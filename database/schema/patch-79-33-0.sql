SET client_min_messages=ERROR;

DROP INDEX karmacache_unique_context_and_category;

ALTER  TABLE karmacache ADD COLUMN project integer
    REFERENCES Project(id);

CREATE UNIQUE INDEX karmacache__unique_context_and_category_by_person
    ON karmacache(person, COALESCE(category, -1), COALESCE(product, -1), 
                  COALESCE(project, -1), COALESCE(distribution, -1),
                  COALESCE(sourcepackagename, -1));

-- Need to update KarmaPersonCategoryCacheView because we don't want it to
-- include the total across all categories.
CREATE OR REPLACE VIEW KarmaPersonCategoryCacheView AS
    SELECT min(karmacache.id) AS id, karmacache.person,
           karmacache.category, sum(karmacache.karmavalue) AS karmavalue
    FROM karmacache
    WHERE karmacache.category IS NOT NULL
    GROUP BY karmacache.person, karmacache.category;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 33, 0);

