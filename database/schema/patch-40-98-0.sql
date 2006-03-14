SET client_min_messages=ERROR;

-- create PPA tables
CREATE TABLE personalpackagearchive (
    id serial PRIMARY KEY,
    person integer NOT NULL CONSTRAINT personalpackagearchive_person_fk
        REFERENCES person(id),
    distrorelease integer NOT NULL CONSTRAINT
        personalpackagearchive_distrorelease_fk REFERENCES distrorelease(id),
    packages integer CONSTRAINT personalpackagearchive_packages_fk
        REFERENCES libraryfilealias(id),
    sources integer CONSTRAINT personalpackagearchive_sources_fk
        REFERENCES libraryfilealias(id),
    release integer CONSTRAINT personalpackagearchive_release_fk
        REFERENCES libraryfilealias(id),
    release_gpg integer CONSTRAINT personalpackagearchive_release_gpg_fk
        REFERENCES libraryfilealias(id),
    datelastupdated timestamp without time zone DEFAULT
        timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone)
        NOT NULL
);

CREATE TABLE personalsourcepackagepublication (
    id serial PRIMARY KEY,
    personalpackagearchive integer NOT NULL CONSTRAINT
        personalsourcepackagepublication_personalpackagearchive_fk
        REFERENCES personalpackagearchive(id),
    sourcepackagerelease integer NOT NULL CONSTRAINT
        personalsourcepackagepublication_sourcepackagerelease_fk
        REFERENCES sourcepackagerelease(id)
);


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 98, 0);
