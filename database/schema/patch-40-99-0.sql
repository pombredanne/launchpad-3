SET client_min_messages=ERROR;

CREATE TABLE SupportContact (
    id SERIAL PRIMARY KEY,
    product INT REFERENCES Product(id),
    distribution INT REFERENCES Distribution(id),
    sourcepackagename INT REFERENCES SourcePackageName(id),
    person INT NOT NULL REFERENCES Person(id)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 99, 0);

