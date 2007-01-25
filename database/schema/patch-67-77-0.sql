SET client_min_messages=ERROR;

DELETE FROM KarmaCache;

CREATE UNIQUE INDEX karmacache__unique_context_and_category_by_person
    ON karmacache(person, category, product, distribution, sourcepackagename);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 77, 0);

