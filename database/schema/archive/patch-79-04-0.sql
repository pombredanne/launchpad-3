SET client_min_messages=ERROR;

DROP INDEX karmacache_unique_context_and_category;

ALTER  TABLE karmacache ADD COLUMN project integer
    REFERENCES Project(id);

-- Drop and recreate indexes used for 'top X contributers', 'top X translators'
-- etc.
DROP INDEX karmacache__category__karmavalue__idx;
DROP INDEX karmacache__distribution__karmavalue__idx;
DROP INDEX karmacache__product__karmavalue__idx;

/*  'top X contributers globally in Launchpad'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category IS NULL
            AND product IS NULL AND project IS NULL AND distribution IS NULL
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__karmavalue__idx
    ON KarmaCache(karmavalue)
    WHERE category IS NULL
        AND product IS NULL AND project IS NULL AND distribution IS NULL;

/*  'top X by category no context'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category=2
            AND product IS NULL AND project IS NULL AND distribution IS NULL
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__category__karmavalue__idx
    ON KarmaCache(category, karmavalue)
    WHERE category IS NOT NULL
        AND product IS NULL AND project IS NULL AND distribution IS NULL;

/*  'top X contributers by product'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category IS NULL AND product=2
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__product__karmavalue__idx
    ON KarmaCache(product, karmavalue)
    WHERE category IS NULL AND product IS NOT NULL;

/*  'top X contributers by product by context'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category=1 AND product=2
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__product__category__karmavalue__idx
    ON KarmaCache(product, category, karmavalue)
    WHERE category IS NOT NULL AND product IS NOT NULL;

/* 'top X contributers by project'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category IS NULL AND project=2
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__project__karmavalue__idx
    ON KarmaCache(project, karmavalue)
    WHERE category IS NULL AND project IS NOT NULL; 

/*  'top X contributers by project by context'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category=1 AND project=2
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__project__category__karmavalue__idx
    ON KarmaCache(project, category, karmavalue) WHERE project IS NOT NULL; 

/*  'top X contributers by distribution'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category IS NULL AND distribution=1 AND sourcepackagename IS NULL
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__distribution__karmavalue__idx
    ON KarmaCache(distribution, karmavalue)
    WHERE category IS NULL
        AND distribution IS NOT NULL AND sourcepackagename IS NULL;

/*  'top X contributers by distribution by category'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category=1 AND distribution=1 AND sourcepackagename IS NULL
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__distribution__category__karmavalue__idx
    ON KarmaCache(distribution, category, karmavalue)
    WHERE category IS NOT NULL
        AND distribution IS NOT NULL AND sourcepackagename IS NULL;

/*  'top X contributers by sourcepackage'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category IS NULL AND distribution=1 AND sourcepackagename=22
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__sourcepackagename__karmavalue__idx
    ON KarmaCache(sourcepackagename, distribution, karmavalue)
    WHERE category IS NULL AND sourcepackagename IS NOT NULL;

/*  'top X contributers by sourcepackage by category'
        SELECT person, karmavalue FROM KarmaCache
        WHERE category=1 AND distribution=1 AND sourcepackagename=22
        ORDER BY karmavalue DESC LIMIT 10;
*/
CREATE INDEX karmacache__sourcepackagename__category__karmavalue__idx
    ON KarmaCache(sourcepackagename, distribution, category, karmavalue)
    WHERE category IS NOT NULL AND sourcepackagename IS NOT NULL;


-- Create UNIQUE contraint. This could also be done using partial indexes,
-- but the result looked confusing and would be harder to maintain, while
-- I expect the advantages of indexes usable by the planner where minimal.
CREATE UNIQUE INDEX karmacache__unq ON KarmaCache(
    person,
    COALESCE(product, -1), 
    COALESCE(sourcepackagename, -1),
    COALESCE(project, -1),
    COALESCE(category, -1),
    COALESCE(distribution, -1)
    );

-- Add some constraints ensuring we have valid context.
ALTER TABLE KarmaCache ADD CONSTRAINT just_product CHECK (
    product IS NULL OR (project IS NULL AND distribution IS NULL)
    );
ALTER TABLE KarmaCache ADD CONSTRAINT just_project CHECK (
    project IS NULL OR (product IS NULL AND distribution IS NULL)
    );
ALTER TABLE KarmaCache ADD CONSTRAINT just_distribution CHECK (
    distribution IS NULL OR (product IS NULL AND project IS NULL)
    );
ALTER TABLE KarmaCache DROP CONSTRAINT sourcepackagename_required_distribution;
ALTER TABLE KarmaCache ADD CONSTRAINT sourcepackagename_requires_distribution
    CHECK (sourcepackagename IS NULL OR distribution IS NOT NULL);

DROP VIEW KarmaPersonCategoryCacheView;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 04, 0);

