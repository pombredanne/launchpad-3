SET client_min_messages=ERROR;

DELETE FROM KarmaCache;

-- Prevent multiple rows with the same context for a given person and category
CREATE UNIQUE INDEX karmacache__unique_context_and_category_by_person
    ON karmacache(person, category, coalesce(product, -1), 
                  coalesce(distribution, -1), coalesce(sourcepackagename, -1));

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 39, 0);

