SET client_min_messages=ERROR;

-- Columns with a NULL category will contain the total karma for that context
-- in all cactegories.
ALTER TABLE KarmaCache ALTER COLUMN category DROP NOT NULL;

-- Rebuild indexes now category is nullable
DROP INDEX karmacache__unique_context_and_category_by_person;
CREATE UNIQUE INDEX karmacache_unique_context_and_category
    ON karmacache (
        person, coalesce(category, -1), coalesce(product, -1), 
        coalesce(distribution, -1), coalesce(sourcepackagename, -1)
        );

DROP INDEX karmacache__category__karmavalue__idx;
CREATE INDEX karmacache__category__karmavalue__idx
    ON KarmaCache(category, karmavalue)
    WHERE category IS NOT NULL;

-- This index is not as useful as it could be, as sourcepackagename
-- Karma always has a distribution
DROP INDEX karmacache__sourcepackagename__karmavalue__idx;
CREATE INDEX karmacache__sourcepackagename__distribution__karmavalue__idx
    ON KarmaCache(sourcepackagename, distribution, karmavalue)
    WHERE sourcepackagename IS NOT NULL;
-- Add a check constraint to ensure this remains true
ALTER TABLE KarmaCache ADD CONSTRAINT sourcepackagename_required_distribution
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 40, 1);

