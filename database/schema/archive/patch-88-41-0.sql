SET client_min_messages=ERROR;

CREATE TABLE FeaturedProject (
    id           serial PRIMARY KEY,
    pillar_name   integer NOT NULL REFERENCES PillarName(id)
);

CREATE INDEX featuredproject__pillar_name__idx
       ON FeaturedProject(pillar_name);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 41, 0);
