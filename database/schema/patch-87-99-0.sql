SET client_min_messages=ERROR;

CREATE TABLE ProductLicense (
    id serial PRIMARY KEY,
    product integer NOT NULL REFERENCES Product(id),
    license integer NOT NULL,
    UNIQUE (product, license)
    );

CREATE INDEX productlicense__license__idx ON ProductLicense(license);


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
