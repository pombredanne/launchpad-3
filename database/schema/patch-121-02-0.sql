SET client_min_messages=ERROR;

CREATE TABLE PackageDiff (
    id serial PRIMARY KEY,
    date_requested timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    requester integer NOT NULL REFERENCES Person(id),
    from_source integer NOT NULL REFERENCES SourcePackageRelease(id),
    to_source integer NOT NULL REFERENCES SourcePackageRelease(id),
    date_fulfilled timestamp without time zone,
    diff_content integer REFERENCES LibraryFileAlias(id),
    CONSTRAINT distinct_sources CHECK (from_source != to_source)
);

CREATE INDEX packagediff__diff_content__idx ON PackageDiff(diff_content);
CREATE INDEX packagediff__requester__idx ON PackageDiff(requester);
CREATE INDEX packagediff__from_source__idx ON PackageDiff(from_source);
CREATE INDEX packagediff__to_source__idx ON PackageDiff(to_source);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 02, 0);
