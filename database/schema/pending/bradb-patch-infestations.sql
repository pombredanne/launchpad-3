SET client_min_messages TO error;

ALTER TABLE Bug ADD CONSTRAINT valid_bug_name CHECK (valid_bug_name(name));

CREATE TABLE BugInfestationType (
    id serial PRIMARY KEY,
    type text NOT NULL
);

CREATE TABLE BugProductInfestation (
    id serial PRIMARY KEY,
    bug integer NOT NULL REFERENCES Bug(id),
    productrelease integer NOT NULL REFERENCES ProductReease(id),
    explicit boolean NOT NULL,
    infestation integer NOT NULL,
    datecreated timestamp NOT NULL DEFAULT 'NOW' AS TIME ZONE 'UTC',
    creator integer NOT NULL,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone not null default timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastmodifiedby integer not null
);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_key UNIQUE (bug, productrelease);

CREATE TABLE BugPackageInfestation (
    id serial NOT NULL,
    bug integer not null,
    sourcepackagerelease integer not null,
    explicit boolean not null,
    infestation integer not null,
    datecreated timestamp without time zone not null default timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    creator integer not null,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone not null default timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastmodifiedby integer not null
);

ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_pkey PRIMARY KEY (id);
ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT bugpackageinfestation_bug_key UNIQUE (bug, sourcepackagerelease);
ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT "$2" FOREIGN KEY (sourcepackagerelease) REFERENCES sourcepackagerelease(id);
ALTER TABLE ONLY bugpackageinfestation
    ADD CONSTRAINT "$3" FOREIGN KEY (infestation) REFERENCES buginfestationtype(id); 
