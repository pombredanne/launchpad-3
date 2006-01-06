SET client_min_messages=ERROR;

DROP TABLE PackageBugContact;

CREATE TABLE PackageBugContact (
    id SERIAL PRIMARY KEY,
    distribution INT NOT NULL REFERENCES Distribution(id),
    sourcepackagename INT NOT NULL REFERENCES SourcePackageName(id),
    bugcontact INT NOT NULL REFERENCES Person(id),
    CONSTRAINT packagebugcontact_distinct_bugcontact
        UNIQUE (sourcepackagename, distribution, bugcontact)
    );
CREATE INDEX packagebugcontact_bugcontact_idx ON PackageBugContact(bugcontact);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 8, 0);

