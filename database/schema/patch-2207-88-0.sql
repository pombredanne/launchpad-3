SET client_min_messages=ERROR;

CREATE TABLE SourcePackageRecipeData (
    id serial PRIMARY KEY,
    base_branch integer NOT NULL REFERENCES Branch,
    recipe_format text NOT NULL,
    deb_version_template text NOT NULL
);

CREATE TABLE SourcePackageRecipeDataInstruction (
    id serial PRIMARY KEY,
    name text NOT NULL, -- NOT NULL?
    type integer NOT NULL, -- MERGE == 1, NEST == 2
    comment text,
    line_number integer NOT NULL,
    branch integer NOT NULL REFERENCES Branch,
    revspec text,
    directory text,
    recipe_data integer REFERENCES SourcePackageRecipeData,
    parent_instruction integer REFERENCES SourcePackageRecipeDataInstruction
);

ALTER TABLE SourcePackageRecipeDataInstruction ADD CONSTRAINT sourcepackagerecipedatainstruction__name__recipe_data
     UNIQUE (name, recipe_data);
ALTER TABLE SourcePackageRecipeDataInstruction ADD CONSTRAINT sourcepackagerecipedatainstruction__line_number__recipe_data
     UNIQUE (line_number, recipe_data);
ALTER TABLE SourcePackageRecipeDataInstruction ADD CONSTRAINT sourcepackagerecipedatainstruction__directory_not_null
     CHECK ((type = 1 AND directory IS NULL) OR (type != 2 AND directory IS NOT NULL));

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

ALTER TABLE SourcePackageRecipe ADD CONSTRAINT sourcepackagerecipe__owner__distroseries__sourcepackagename__name
     UNIQUE (owner, distroseries, sourcepackagename, name);

ALTER TABLE SourcePackageRecipe ADD CONSTRAINT sourcepackagerecipedata__recipe_data
     UNIQUE (recipe_data);

CREATE TABLE SourcePackageBuild (
    id serial PRIMARY KEY,
    -- most of this is just copied from Build

    -- I've dropped: processor, sourcepackagerelease, pocket, dependencies
    -- changed: distroarchseries to distroseries
    -- added: recipe and manifest
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    distroseries integer NOT NULL REFERENCES distroseries,
    sourcepackagename integer NOT NULL REFERENCES SourcePackageName,
    build_state integer NOT NULL,
    date_built timestamp without time zone,
    build_duration interval,
    build_log integer REFERENCES libraryfilealias,
    builder integer REFERENCES builder,
    date_first_dispatched timestamp without time zone,
    requester integer REFERENCES Person,
    recipe integer REFERENCES SourcePackageRecipe NOT NULL,
    manifest integer REFERENCES SourcePackageRecipeData
);

ALTER TABLE SourcePackageBuild ADD CONSTRAINT sourcepackagebuild__manifest
    UNIQUE (manifest);

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

ALTER TABLE BuildSourcePackageFromRecipeJob ADD CONSTRAINT buildsourcepackagefromrecipejob__source_package_build
    UNIQUE (source_package_build);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 88, 0);
