SET client_min_messages=ERROR;

CREATE TABLE SourcePackageRecipe (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL REFERENCES Person,
    owner integer NOT NULL REFERENCES Person,
    distroseries integer NOT NULL REFERENCES DistroSeries,
    sourcepackagename integer NOT NULL REFERENCES SourcePackageName,
    name text NOT NULL,
    recipe text NOT NULL
);

CREATE UNIQUE INDEX sourcepackagerecipe__owner_distroseries_sourcepackagename_name
    ON SourcePackageRecipe
 USING btree(owner, distroseries, sourcepackagename, name);

CREATE TABLE SourcePackageRecipeBranch (
    id serial PRIMARY KEY,
    sourcepackagerecipe integer NOT NULL REFERENCES SourcePackageRecipe,
    branch integer NOT NULL REFERENCES branch
);

CREATE INDEX sourcepackagerecipebranch__sourcepackagerecipe
    ON SourcePackageRecipeBranch USING btree(sourcepackagerecipe);
CREATE INDEX sourcepackagerecipebranch__branch
    ON SourcePackageRecipeBranch USING btree(branch);

CREATE TABLE BuildSourcePackageFromRecipeJob (
    id serial PRIMARY KEY,
    job integer NOT NULL REFERENCES Job,
    recipe integer NOT NULL REFERENCES SourcePackageRecipe,
    archive integer NOT NULL REFERENCES Archive
    -- requester is on Job already!
);

-- What about the results of building the package?  the manifest and
-- the log, mainly.

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 88, 0);

