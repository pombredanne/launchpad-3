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

CREATE INDEX PersonalPackageArchive__distrorelease__idx
    ON PersonalPackageArchive(distrorelease);
CREATE INDEX PersonalPackageArchive__datelastupdated__idx
    ON PersonalPackageArchive(datelastupdated);

-- Indexes for people merge and garbage collection to work happily
CREATE INDEX PersonalPackageArchive__person__idx
    ON PersonalPackageArchive(person);
CREATE INDEX PersonalPackageArchive__packages__idx
    ON PersonalPackageArchive(packages) WHERE packages IS NOT NULL;
CREATE INDEX PersonalPackageArchive__sources__idx
    ON PersonalPackageArchive(sources) WHERE sources IS NOT NULL;
CREATE INDEX PersonalPackageArchive__release__idx
    ON PersonalPackageArchive(release) WHERE release IS NOT NULL;
CREATE INDEX PersonalPackageArchive__release_gpg__idx
    ON PersonalPackageArchive(release_gpg) WHERE release_gpg IS NOT NULL;


CREATE TABLE personalsourcepackagepublication (
    id serial PRIMARY KEY,
    personalpackagearchive integer NOT NULL CONSTRAINT
        personalsourcepackagepublication_personalpackagearchive_fk
        REFERENCES personalpackagearchive(id),
    sourcepackagerelease integer NOT NULL CONSTRAINT
        personalsourcepackagepublication_sourcepackagerelease_fk
        REFERENCES sourcepackagerelease(id),
    CONSTRAINT personalsourcepackagepublication_key
        UNIQUE (personalpackagearchive, sourcepackagerelease)
);

-- Ensure the DB matches the sqlobject class
ALTER TABLE binarypackagerelease ALTER COLUMN priority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 30, 0);