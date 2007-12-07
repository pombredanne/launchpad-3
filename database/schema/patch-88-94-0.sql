SET client_min_messages=ERROR;

CREATE TABLE FeaturedProject (
    id           serial PRIMARY KEY,
    name         text NOT NULL REFERENCES PillarName(name)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 94, 0);
