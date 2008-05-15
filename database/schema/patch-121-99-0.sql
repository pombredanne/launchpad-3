SET client_min_messages=ERROR;

CREATE TABLE ProductSeriesCodeImportMapping (
    id serial PRIMARY KEY,
    productseries integer NOT NULL UNIQUE REFERENCES ProductSeries (id),
    codeimport integer NOT NULL UNIQUE REFERENCES CodeImport (id));
);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
