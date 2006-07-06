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

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 09, 0);

