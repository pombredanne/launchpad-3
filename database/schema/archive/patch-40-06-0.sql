SET client_min_messages=ERROR;

CREATE TABLE PackageBugContact (
    distribution INT NOT NULL REFERENCES Distribution(id),
    sourcepackagename INT NOT NULL REFERENCES SourcePackageName(id),
    bugcontact INT NOT NULL REFERENCES Person(id),
    CONSTRAINT packagebugcontact_distinct_bugcontact
        UNIQUE (sourcepackagename, distribution, bugcontact)
    );
CREATE INDEX packagebugcontact_bugcontact_idx ON PackageBugContact(bugcontact);

ALTER TABLE Distribution ADD COLUMN bugcontact INT REFERENCES Person (id);
ALTER TABLE Product ADD COLUMN bugcontact INT REFERENCES Person(id);

-- In case we list what people are bug contacts for in their /people area
CREATE INDEX distribution_bugcontact_idx ON Distribution(bugcontact);
CREATE INDEX product_bugcontact_idx ON Product(bugcontact);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 6, 0);

