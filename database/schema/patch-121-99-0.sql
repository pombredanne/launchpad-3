SET client_min_messages=ERROR;

CREATE TABLE ArchivePermission (
    id INTEGER NOT NULL,
    date_created timestamp without time zone
        DEFAULT timezone('UTC'::text, now()) NOT NULL,
    archive INTEGER NOT NULL,
    permission INTEGER NOT NULL,
    person INTEGER NOT NULL,
    component INTEGER,
    sourcepackagename INTEGER);

CREATE SEQUENCE archivepermission_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE archivepermission_id_seq OWNED BY ArchivePermission.id;

ALTER TABLE ArchivePermission ALTER COLUMN id
    SET DEFAULT nextval('archivepermission_id_seq'::regclass);


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


ALTER TABLE ArchivePermission
    ADD CONSTRAINT archivepermission_component_fk
        FOREIGN KEY (component) REFERENCES component(id),
    ADD CONSTRAINT archivepermission_person_fk
        FOREIGN KEY (person) REFERENCES person(id),
    ADD CONSTRAINT archivepermission_archive_fk
        FOREIGN KEY (archive) REFERENCES archive(id),
    ADD CONSTRAINT archivepermission_sourcepackagename_fk
        FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
