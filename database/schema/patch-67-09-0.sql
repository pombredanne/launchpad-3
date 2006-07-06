SET client_min_messages=ERROR;

ALTER TABLE Karma ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE Karma ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE Karma ADD COLUMN sourcepackagename INTEGER REFERENCES SourcepackageName(id);

ALTER TABLE KarmaCache ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE KarmaCache ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE KarmaCache ADD COLUMN sourcepackagename INTEGER REFERENCES SourcepackageName(id);

ALTER TABLE KarmaCache DROP CONSTRAINT category_person_key;

ALTER TABLE KarmaCache 
    ADD CONSTRAINT category_product_distro_sourcepackage_key
        UNIQUE (category, product, distribution, sourcepackagename, person);

-- SQLObject needs an id column in all tables, but we use a GROUP BY when
-- generating this view and thus we have to cheat and get the smallest id,
-- which shouldn't be a problem.
CREATE VIEW KarmaPersonCategoryCacheView AS
    SELECT min(id) as id, person, category, SUM(karmavalue) AS karmavalue
    FROM KarmaCache
    GROUP BY category, person, category;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 09, 0);

