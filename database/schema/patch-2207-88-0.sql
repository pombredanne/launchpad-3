SET client_min_messages=ERROR;

CREATE TABLE SourcePackageRecipeData (
    id serial PRIMARY KEY,
    recipe text NOT NULL
);

CREATE TABLE SourcePackageRecipeDataBranch (
    id serial PRIMARY KEY,
    sourcepackagerecipedata integer NOT NULL REFERENCES SourcePackageRecipeData,
    branch integer NOT NULL REFERENCES branch
);

CREATE INDEX sourcepackagerecipedatabranch__sourcepackagerecipe
    ON SourcePackageRecipeDataBranch USING btree(sourcepackagerecipedata);
CREATE INDEX sourcepackagerecipedatabranch__branch
    ON SourcePackageRecipeDataBranch USING btree(branch);

-- unique on (branch, sourcepackagerecipe) ??

CREATE TABLE SourcePackageRecipe (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    date_last_modified timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    registrant integer NOT NULL REFERENCES Person,
    owner integer NOT NULL REFERENCES Person,
    distroseries integer NOT NULL REFERENCES DistroSeries,
    sourcepackagename integer NOT NULL REFERENCES SourcePackageName,
    name text NOT NULL,
    recipe_data integer NOT NULL REFERENCES SourcePackageRecipeData
);

CREATE UNIQUE INDEX sourcepackagerecipe__owner_distroseries_sourcepackagename_name
    ON SourcePackageRecipe
 USING btree(distroseries, sourcepackagename, name);

CREATE TABLE SourcePackageBuild (
    id serial PRIMARY KEY,
    -- most of this is just copied from Build

    -- I've dropped: processor, sourcepackagerelease, pocket, dependencies
    -- changed: distroarchseries to distroseries
    -- add: recipe and manifest
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    distroseries integer NOT NULL REFERENCES distroseries,
    sourcepacakgename integer NOT NULL REFERENCES SourcePackageName,
    build_state integer NOT NULL,
    date_built timestamp without time zone,
    build_duration interval,
    build_log integer REFERENCES libraryfilealias,
    builder integer REFERENCES builder,
    date_first_dispatched timestamp without time zone,
    requester integer REFERENCES Person,
    recipe integer REFERENCES SourcePackageRecipe,
    manifest integer REFERENCES SourcePackageRecipeData
);

CREATE TABLE SourcePackageBuildUpload (
    id serial PRIMARY KEY,
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    registrant integer NOT NULL REFERENCES Person,
    source_package_build integer NOT NULL REFERENCES SourcePackageBuild,
    archive integer NOT NULL REFERENCES Archive,
    upload_log integer REFERENCES LibraryFileAlias,
    state integer NOT NULL -- an enum, WAITING/UPLOADED/FAILED or something like that.
);

-- indexes for SourcePackageBuildUpload I guess

ALTER TABLE SourcePackageRelease
  ADD COLUMN source_package_build integer REFERENCES SourcePackageBuild;

CREATE TABLE BuildSourcePackageFromRecipeJob (
    id serial PRIMARY KEY,
    job integer NOT NULL REFERENCES Job,
    source_package_build integer REFERENCES SourcePackageBuild
);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 88, 0);
