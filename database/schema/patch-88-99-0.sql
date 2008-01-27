SET client_min_messages=ERROR;

CREATE TABLE PackageDiff (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    requester integer NOT NULL REFERENCES Person(id),
    from_source integer NOT NULL REFERENCES SourcePackageRelease(id),
    to_source integer NOT NULL REFERENCES SourcePackageRelease(id),
    date_fulfilled timestamp without time zone,
    diff_content integer REFERENCES LibraryFileAlias(id),
    CONSTRAINT distinct_sources CHECK (from_source != to_source)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
