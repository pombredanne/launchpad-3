SET client_min_messages=ERROR;

-- Package sets facilitate the grouping of packages for purposes like
-- the control of upload permissions, the calculation of build and
-- runtime package dependencies etc.
CREATE TABLE packageset (
  id serial PRIMARY KEY,
  date_created timestamp without time zone NOT NULL
    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  owner integer NOT NULL
    CONSTRAINT packageset__owner__fk REFERENCES person,
  name text NOT NULL CHECK (valid_name(name)) UNIQUE,
  description text NOT NULL
);

-- ArchivePermission table modifications needed to support the
-- definition of uload permissions on package set level.
-- Add a 'packageset' foreign key so we can tie archive permissions to
-- package sets.
ALTER TABLE archivepermission ADD COLUMN packageset integer;
  -- This flag is set for package sets containing high-profile packages
  -- that must not break and/or require specialist skills for proper
  -- handling e.g. the kernel.
ALTER TABLE archivepermission ADD COLUMN
  explicit boolean DEFAULT false NOT NULL;
ALTER TABLE ONLY archivepermission
  ADD CONSTRAINT archivepermission__packageset__fk
  FOREIGN KEY (packageset) REFERENCES packageset(id);

-- Change the existing constraint so that the archive permission may be
-- tied to one of the following only: component, sourcepackagename or
-- packageset.
ALTER TABLE ONLY archivepermission
  DROP CONSTRAINT component_or_sourcepackagename;
ALTER TABLE archivepermission ADD CONSTRAINT one_target CHECK
    (null_count(ARRAY[packageset, component, sourcepackagename]) = 2);

---------------- package sets and source package names ---------------------
-- The 'packagesetsources' table associates package sets and source
-- package names e.g. for the purpose of controling package upload
-- permissions. Please note that this table only captures the sets and
-- source package names that are associated *directly*.
CREATE TABLE packagesetsources (
  id serial PRIMARY KEY,
  packageset integer NOT NULL,
  sourcepackagename integer NOT NULL
);

ALTER TABLE ONLY packagesetsources
  ADD CONSTRAINT packagesetsources__packageset__sourcepackagename__key
  UNIQUE (packageset, sourcepackagename);
ALTER TABLE ONLY packagesetsources
  ADD CONSTRAINT packagesetsources__packageset__fk
  FOREIGN KEY (packageset) REFERENCES packageset(id);
ALTER TABLE ONLY packagesetsources
  ADD CONSTRAINT sourcepackagenamesources__sourcepackagename__fk
  FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);


---------------- package sets and hierarchies ---------------------
-- Package sets may form a set-subset hierarchy; this table facilitates
-- the definition of these relationships. A set L may be the subset of
-- many other sets as well as having many subsets of its own.

-- Let A have a subset B and B have a subset C. In that case we would
-- have the following rows in the 'packagesetinclusion' table:
--      A, B
--      B, C
CREATE TABLE packagesetinclusion (
  id serial PRIMARY KEY,
  parent integer NOT NULL,
  child integer NOT NULL
);
ALTER TABLE ONLY packagesetinclusion
  ADD CONSTRAINT packagepayerinclusion__parent__child__key
  UNIQUE (parent, child);
ALTER TABLE ONLY packagesetinclusion
  ADD CONSTRAINT packagesetinclusion__parent__fk
  FOREIGN KEY (parent) REFERENCES packageset(id);
ALTER TABLE ONLY packagesetinclusion
  ADD CONSTRAINT packagesetinclusion__child__fk
  FOREIGN KEY (child) REFERENCES packageset(id);

-- In order to facilitate the querying of set-subset relationships an
-- expanded or flattened representation of the set-subset hierarchy shall
-- be provided in addition.
-- Let A have a subset B and B have a subset C. In that case we would have
-- the following rows in the 'flatpackagesetinclusion' table:
--      A, B
--      A, C
--      B, C
-- Please note that each set shall be defined to include itself (in order to
-- make querying easier) resulting in the following additional data:
--      A, A
--      B, B
--      C, C
-- Please note also that the 'flatpackagesetinclusion' table will be
-- maintained by INSERT/DELETE triggers on the 'packagesetinclusion' and on
-- the 'packageset' table.
CREATE TABLE flatpackagesetinclusion (
  id serial PRIMARY KEY,
  parent integer NOT NULL,
  child integer NOT NULL
);
ALTER TABLE ONLY flatpackagesetinclusion
  ADD CONSTRAINT flatpackagesetinclusion__parent__child__key
  UNIQUE (parent, child);
ALTER TABLE ONLY flatpackagesetinclusion
  ADD CONSTRAINT flatpackagesetinclusion__parent__fk
  FOREIGN KEY (parent) REFERENCES packageset(id);
ALTER TABLE ONLY flatpackagesetinclusion
  ADD CONSTRAINT flatpackagesetinclusion__child__fk
  FOREIGN KEY (child) REFERENCES packageset(id);

CREATE TRIGGER packageset_inserted_trig
  AFTER INSERT ON packageset
  FOR EACH ROW
  EXECUTE PROCEDURE packageset_inserted_trig();

CREATE TRIGGER packageset_deleted_trig
  BEFORE DELETE ON packageset
  FOR EACH ROW
  EXECUTE PROCEDURE packageset_deleted_trig();

CREATE TRIGGER packagesetinclusion_inserted_trig
  AFTER INSERT ON packagesetinclusion
  FOR EACH ROW
  EXECUTE PROCEDURE packagesetinclusion_inserted_trig();

CREATE TRIGGER packagesetinclusion_deleted_trig
  BEFORE DELETE ON packagesetinclusion
  FOR EACH ROW
  EXECUTE PROCEDURE packagesetinclusion_deleted_trig();

CREATE INDEX packageset__owner__idx ON packageset(owner);
CREATE INDEX packagesetinclusion__child__idx
    ON packagesetinclusion(child);
CREATE INDEX packagesetsources__sourcepackagename__idx
    ON PackageSetSources(sourcepackagename);
CREATE INDEX archivepermission__packageset__idx
    ON ArchivePermission(packageset) WHERE packageset IS NOT NULL;
CREATE INDEX flatpackagesetinclusion__child__idx
    ON FlatPackageSetInclusion(child);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 45, 0);
