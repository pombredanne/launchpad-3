SET client_min_messages=ERROR;

/*
  We need a few status flags on project / product to ensure that we get 
  the chance to sanitise the data that gets created. For the moment these 
  won't influence search
  results etc, but in time that may happen.
*/

ALTER TABLE Project ADD COLUMN reviewed boolean;
ALTER TABLE Project ALTER COLUMN reviewed SET DEFAULT False;
UPDATE Project SET reviewed = False WHERE reviewed IS NULL;
ALTER TABLE Project ALTER COLUMN reviewed SET NOT NULL;

ALTER TABLE Project ADD COLUMN active boolean;
ALTER TABLE Project ALTER COLUMN active SET DEFAULT True;
UPDATE Project SET active = True WHERE active IS NULL;
ALTER TABLE Project ALTER COLUMN active SET NOT NULL;


ALTER TABLE Product ADD COLUMN reviewed boolean;
ALTER TABLE Product ALTER COLUMN reviewed SET DEFAULT False;
UPDATE Product SET reviewed = False WHERE reviewed IS NULL;
ALTER TABLE Product ALTER COLUMN reviewed SET NOT NULL;


ALTER TABLE Product ADD COLUMN active boolean;
ALTER TABLE Product ALTER COLUMN active SET DEFAULT True;
UPDATE Product SET active = True WHERE active IS NULL;
ALTER TABLE Product ALTER COLUMN active SET NOT NULL;

/* POTemplate stuff for Carlos */
ALTER TABLE POTemplate ADD rawfile text;
ALTER TABLE POTemplate ADD rawimporter integer REFERENCES Person(id);
ALTER TABLE POTemplate ADD daterawimport timestamp without time zone;
ALTER TABLE POTemplate ADD rawimportstatus integer;
ALTER TABLE POTemplate ALTER daterawimport set default (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL)));

ALTER TABLE POFile ADD rawfile text;
ALTER TABLE POFile ADD rawimporter integer REFERENCES Person(id);
ALTER TABLE POFile ADD daterawimport timestamp without time zone;
ALTER TABLE POFile ADD rawimportstatus integer;
ALTER TABLE POFile ALTER daterawimport set default (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POFile ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL)));

/* 
    Fix some residual objects with bad names
*/
ALTER TABLE bugsystem_pkey RENAME TO bugtracker_pkey;
ALTER TABLE bugsystemtype_name_key RENAME TO bugtrackertype_name_key;
ALTER TABLE bugsystemtype_pkey RENAME TO bugtrackertype_pkey;

UPDATE LaunchpadDatabaseRevision SET major=5, minor=3, patch=0;
