SET client_min_messages TO error;

ALTER TABLE Bug ADD CONSTRAINT valid_bug_name CHECK (valid_bug_name(name));

/*
 XXX Known Issues with this patch:

  - creator is NOT NULL but explicit=False would imply that the infestation
    was created automatically.  Should we allow creator to be NULL and say
    the a NULL creator implies explicity=false, so we can get rid of the
    explicit field altogether?

  - creator / verifiedby seem inconsistent. Perhaps verifier? What does the
    rest of the db do?
*/

CREATE TABLE BugProductInfestation (
    id serial CONSTRAINT bugproductinfestation_pkey PRIMARY KEY,
    bug integer NOT NULL 
        CONSTRAINT bugproductinfestation_bug_fk 
        REFERENCES Bug(id),
    productrelease integer NOT NULL
        CONSTRAINT bugproductinfestation_productrelease_fk 
        REFERENCES ProductRelease(id),
    explicit boolean NOT NULL,
    infestationstatus integer NOT NULL,
    datecreated timestamp without time zone 
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    creator integer NOT NULL
        CONSTRAINT bugproductinfestation_creator_fk
        REFERENCES Person(id),
    dateverified timestamp without time zone,
    verifiedby integer
        CONSTRAINT bugproductinfestation_verifiedby_fk
        REFERENCES Person(id),
    lastmodified timestamp without time zone
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    lastmodifiedby integer NOT NULL
        CONSTRAINT bugproductinfestation_lastmodifiedby_fk
        REFERENCES Person(id),
    CONSTRAINT bugproductinfestation_bug_key UNIQUE (bug, productrelease)
);

CREATE TABLE BugPackageInfestation (
    id serial CONSTRAINT bugpackageinfestation_pkey PRIMARY KEY,
    bug integer not null
        CONSTRAINT bugpackageinfestation_bug_fk
        REFERENCES Bug(id),
    sourcepackagerelease integer not null
        CONSTRAINT bugpackageinfestation_sourcepackagerelease_fk
        REFERENCES SourcePackageRelease(id),
    explicit boolean not null,
    infestationstatus integer not null,
    datecreated timestamp without time zone 
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    creator integer not null
        CONSTRAINT bugpackageinfestation_creator_fk
        REFERENCES Person(id),
    dateverified timestamp without time zone,
    verifiedby integer
        CONSTRAINT bugpackageinfestation_verifiedby_fk
        REFERENCES Person(id),
    lastmodified timestamp without time zone 
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    lastmodifiedby integer NOT NULL
        CONSTRAINT bugpackageinfestation_lastmodifiedby_fk
        REFERENCES Person(id),
    CONSTRAINT bugpackageinfestation_bug_key UNIQUE (bug, sourcepackagerelease)
);


