SET client_min_messages=ERROR;

CREATE TABLE CustomLanguageCode(
    id SERIAL PRIMARY KEY,
    product integer REFERENCES Product(id),
    distribution integer REFERENCES Distribution(id),
    sourcepackagename integer REFERENCES SourcePackageName(id),
    language_code text not null,
    language integer REFERENCES Language(id));

ALTER TABLE CustomLanguageCode
    ADD CONSTRAINT product_or_distro CHECK (
        (product IS NULL) <> (distribution IS NULL));

ALTER TABLE CustomLanguageCode
    ADD CONSTRAINT distro_and_sourcepackage CHECK (
        (sourcepackagename IS NULL) = (distribution IS NULL));

CREATE UNIQUE INDEX
    customlanguagecode__product__code__key
    ON CustomLanguageCode(product, language_code)
    WHERE product IS NOT NULL;

CREATE UNIQUE INDEX
    customlanguagecode__distribution__sourcepackagename__code__key
    ON CustomLanguageCode(distribution, sourcepackagename, language_code)
    WHERE distribution IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 53, 0);
