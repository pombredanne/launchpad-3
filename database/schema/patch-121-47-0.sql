SET client_min_messages=ERROR;

CREATE TABLE ArchivePermission (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    person INTEGER NOT NULL
        CONSTRAINT archivepermission__person__fk REFERENCES Person,
    permission INTEGER NOT NULL,
    archive INTEGER NOT NULL
        CONSTRAINT archivepermission__archive__fk REFERENCES Archive,
    component INTEGER
        CONSTRAINT archivepermission__component__fk REFERENCES Component,
    sourcepackagename INTEGER
        CONSTRAINT archivepermission__sourcepackagename__fk
        REFERENCES SourcepackageName
);


/*
= Constraints and indexes =

Typical access will be by:
* permission, archive, component (to get (a list of) users)
* permission, archive, sourcepackageaname (to get (a list of) users)
* person, permission, archive, sourcepackagename (to determine whether
   "person" has rights to the package)
* person, permission. archive, component (to determine whether "person"
   has rights to the component)

Constraints:
The Archive/Component must be unique.

*/

-- There won't be many records for a given person, so a simple index on
-- person will be fine for queries and person merge
CREATE INDEX archivepermission__person__archive__idx
    ON ArchivePermission(person, archive);

-- Allow fast lookups
CREATE INDEX archivepermission__archive__component__permission__idx
    ON ArchivePermission(archive, component, permission);

CREATE INDEX archivepermission__archive__sourcepackagename__permission__idx
    ON ArchivePermission(archive, sourcepackagename, permission);

-- Within an archive, specific permissions are supported for a component
-- or a sourcepackage. Not a sourcepackage in a particular component.
-- So only one of component or sourcepackagename can be set.
ALTER TABLE ArchivePermission
    ADD CONSTRAINT component_or_sourcepackagename
    CHECK (component IS NULL OR sourcepackagename IS NULL);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 47, 0);
