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

/*
 XXX removed by Mark Shuttleworth, plese see dbschema.py
CREATE TABLE BugInfestationType (
    id serial PRIMARY KEY,
    type text NOT NULL
);
*/

CREATE TABLE BugProductInfestation (
    id serial NOT NULL,
    bug integer NOT NULL,
    productrelease integer NOT NULL,
    explicit boolean NOT NULL,
    infestationstatus integer NOT NULL,
    datecreated timestamp without time zone not null default timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    creator integer NOT NULL,
    dateverified timestamp without time zone,
    verifiedby integer,
    lastmodified timestamp without time zone not null default timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone),
    lastmodifiedby integer not null
);

ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_pkey PRIMARY KEY (id);
ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT bugproductinfestation_bug_key UNIQUE (bug, productrelease);
ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT "$1" FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE ONLY bugproductinfestation
    ADD CONSTRAINT "$2" FOREIGN KEY (productrelease) REFERENCES productrelease(id);

COMMENT ON TABLE BugProductInfestation IS 'A BugProductInfestation records the impact that a bug is known to have on a specific productrelease. This allows us to track the versions of a product that are known to be affected or unaffected by a bug.';

COMMENT ON COLUMN BugProductInfestation.bug IS 'The Bug that infests this product release.';

COMMENT ON COLUMN BugProductInfestation.productrelease IS 'The product (software) release that is infested with the bug. This points at the specific release version, such as "apache 2.0.48".';

COMMENT ON COLUMN BugProductInfestation.explicit IS 'This field records whether or not the infestation was documented by a user of the system, or inferred from some other source such as the fact that it is documented to affect prior and subsequent releases of the product.';

COMMENT ON COLUMN BugProductInfestation.infestationstatus IS 'The nature of the bug infestation for this product release. Values are documented in dbschema.BugInfestationStatus, and include AFFECTED, UNAFFECTED, FIXED and VICTIMISED. See the dbschema.py file for details.';

COMMENT ON COLUMN BugProductInfestation.creator IS 'The person who recorded this infestation. Typically, this is the user who reports the specific problem on that specific product release.';

COMMENT ON COLUMN BugProductInfestation.dateverified IS 'The timestamp when the problem was verified on that specific release. This a small step towards a complete workflow for defect verification and management on specific releases.';

COMMENT ON COLUMN BugProductInfestation.lastmodified IS 'The timestamp when this infestation report was last modified in any way. For example, when the infestation was adjusted, or it was verified, or otherwise modified.';

COMMENT ON COLUMN BugProductInfestation.lastmodifiedby IS 'The person who touched this infestation report last, in any way.';

CREATE TABLE BugPackageInfestation (
    id serial NOT NULL,
    bug integer not null,
    sourcepackagerelease integer not null,
    explicit boolean not null,
    infestationstatus integer not null,
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

COMMENT ON TABLE BugPackageInfestation IS 'A BugPackageInfestation records the impact that a bug is known to have on a specific sourcepackagerelease. This allows us to track the versions of a package that are known to be affected or unaffected by a bug.';

COMMENT ON COLUMN BugPackageInfestation.bug IS 'The Bug that infests this source package release.';

COMMENT ON COLUMN BugPackageInfestation.sourcepackagerelease IS 'The package (software) release that is infested with the bug. This points at the specific source package release version, such as "apache 2.0.48-1".';

COMMENT ON COLUMN BugPackageInfestation.explicit IS 'This field records whether or not the infestation was documented by a user of the system, or inferred from some other source such as the fact that it is documented to affect prior and subsequent releases of the package.';

COMMENT ON COLUMN BugPackageInfestation.infestationstatus IS 'The nature of the bug infestation for this source package release. Values are documented in dbschema.BugInfestationStatus, and include AFFECTED, UNAFFECTED, FIXED and VICTIMISED. See the dbschema.py file for details.';

COMMENT ON COLUMN BugPackageInfestation.creator IS 'The person who recorded this infestation. Typically, this is the user who reports the specific problem on that specific package release.';

COMMENT ON COLUMN BugPackageInfestation.dateverified IS 'The timestamp when the problem was verified on that specific release. This a small step towards a complete workflow for defect verification and management on specific releases.';

COMMENT ON COLUMN BugPackageInfestation.lastmodified IS 'The timestamp when this infestation report was last modified in any way. For example, when the infestation was adjusted, or it was verified, or otherwise modified.';

COMMENT ON COLUMN BugPackageInfestation.lastmodifiedby IS 'The person who touched this infestation report last, in any way.';

