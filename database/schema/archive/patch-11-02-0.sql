SET client_min_messages=ERROR;

CREATE TABLE Mirror(
    id              serial PRIMARY KEY,
    owner           integer NOT NULL CONSTRAINT mirror_owner_fk
                    REFERENCES Person,
    baseurl         text NOT NULL,
    country         integer NOT NULL CONSTRAINT mirror_country_fk
                    REFERENCES Country,
    name            text NOT NULL UNIQUE,
    description     text NOT NULL,
    freshness       integer NOT NULL DEFAULT 99,
    lastcheckeddate timestamp without time zone,
    approved        boolean NOT NULL DEFAULT FALSE
);


CREATE TABLE MirrorContent(
    id                serial PRIMARY KEY,
    mirror            integer NOT NULL CONSTRAINT mirrorcontent_mirror_fk
                        REFERENCES Mirror,
    distroarchrelease integer NOT NULL
                        CONSTRAINT mirrorcontent_distroarchrelease_fk
                        REFERENCES DistroArchRelease,
    component         INTEGER NOT NULL CONSTRAINT mirrorcontent_component_fk
                        REFERENCES Component
);

CREATE TABLE MirrorSourceContent(
    id                serial PRIMARY KEY,
    mirror            integer NOT NULL CONSTRAINT mirrorsourcecontent_mirror_fk
                        REFERENCES Mirror ,
    distrorelease     integer NOT NULL
                        CONSTRAINT mirrorsourcecontent_distrorelease_fk
                        REFERENCES DistroRelease,
    component         INTEGER NOT NULL
                        CONSTRAINT mirrorsourcecontent_component_fk
                        REFERENCES Component
);

INSERT INTO LaunchpadDatabaseRevision VALUES (11,2,0);

