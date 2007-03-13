SET client_min_messages=ERROR;

ALTER TABLE Karma ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE Karma ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE Karma ADD COLUMN sourcepackagename INTEGER
    REFERENCES SourcepackageName(id);

ALTER TABLE KarmaCache ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE KarmaCache ADD COLUMN distribution INTEGER
    REFERENCES Distribution(id);
ALTER TABLE KarmaCache ADD COLUMN sourcepackagename INTEGER
    REFERENCES SourcepackageName(id);

ALTER TABLE KarmaCache DROP CONSTRAINT category_person_key;

-- This index is needed to make select by person or group by person,category
-- work efficiently.
CREATE INDEX karmacache__person__category__idx ON KarmaCache(person, category);

-- This index is needed to allow us to select high scorers per category.
-- Do we do this?
CREATE INDEX karmacache__category__karmavalue__idx
    ON KarmaCache(category, karmavalue);

-- This indexes are needed to allow us to select high scorers by context,
-- which is a use case descrived in person.txt
CREATE INDEX karmacache__product__karmavalue__idx
    ON KarmaCache(product, karmavalue) WHERE product IS NOT NULL;
CREATE INDEX karmacache__distribution__karmavalue__idx
    ON KarmaCache(distribution, karmavalue) WHERE distribution IS NOT NULL;
CREATE INDEX karmacache__sourcepackagename__karmavalue__idx
    ON KarmaCache(sourcepackagename, karmavalue)
    WHERE sourcepackagename IS NOT NULL;

-- This constraint isn't useful as NULLs are allowed in most of the columns
-- The original constraint was really only there to speed grouping operations.
-- ALTER TABLE KarmaCache 
--     ADD CONSTRAINT category_product_distro_sourcepackage_key
--         UNIQUE (category, product, distribution, sourcepackagename, person);

-- SQLObject needs an id column in all tables, but we use a GROUP BY when
-- generating this view and thus we have to cheat and get the smallest id,
-- which shouldn't be a problem.
CREATE VIEW KarmaPersonCategoryCacheView AS
    SELECT min(id) as id, person, category, SUM(karmavalue) AS karmavalue
    FROM KarmaCache
    GROUP BY person, category;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 03, 0);
