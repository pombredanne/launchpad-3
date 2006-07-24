SET client_min_messages=ERROR;

CREATE TABLE SupportContact (
    id SERIAL PRIMARY KEY,
    product INT REFERENCES Product(id),
    distribution INT REFERENCES Distribution(id),
    sourcepackagename INT REFERENCES SourcePackageName(id),
    person INT NOT NULL REFERENCES Person(id),
    CONSTRAINT supportcontact__product__person__key UNIQUE (product, person),
    CONSTRAINT valid_target CHECK (
        (product IS NULL <> distribution IS NULL)
        AND (product IS NULL OR sourcepackagename IS NULL)
        ),
    CONSTRAINT supportcontact__distribution__sourcepackagename__person__key
        UNIQUE (distribution, sourcepackagename, person)
    );

-- Only one (distribution,person,sourcepackagename IS NULL)
CREATE UNIQUE INDEX foo
    ON SupportContact(distribution, person)
    WHERE sourcepackagename IS NULL;

-- Required for people merge to not suck
CREATE INDEX supportcontact__person__idx ON SupportContact(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 33, 0);
