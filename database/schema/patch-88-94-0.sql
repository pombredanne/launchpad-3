SET client_min_messages=ERROR;

CREATE TABLE FeaturedProject (
    id           serial PRIMARY KEY,
    pillarname   integer NOT NULL REFERENCES PillarName(id)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 94, 0);
