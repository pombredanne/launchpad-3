
/* Support Lucille's configuration

    Configuration information for Lucielle - the config data will be
    migrated to real database tables and columns when the needs are
    finalized.
*/

ALTER TABLE distribution ADD COLUMN lucilleconfig text;
ALTER TABLE distrorelease ADD COLUMN lucilleconfig text;

/* Rename SourcePackageUpload and add serial primary key */

ALTER TABLE SourcePackageUpload RENAME TO SourcePackagePublishing;
ALTER TABLE SourcePackagePublishing ADD COLUMN id integer;
CREATE SEQUENCE sourcepackagepublishing_id_seq;
ALTER TABLE SourcePackagePublishing 
    ALTER COLUMN id SET DEFAULT nextval('sourcepackagepublishing_id_seq');

/*
 * Add some columns to sourcepackagepublishing
 */
ALTER TABLE ONLY sourcepackagepublishing ADD COLUMN component integer;
ALTER TABLE ONLY sourcepackagepublishing ADD COLUMN section integer;
ALTER TABLE ONLY sourcepackagepublishing ALTER COLUMN component SET NOT NULL;
ALTER TABLE ONLY sourcepackagepublishing ALTER COLUMN section SET NOT NULL;
ALTER TABLE ONLY sourcepackagepublishing 
    ADD CONSTRAINT sourcepackagepublishing_component_fk 
        FOREIGN KEY (component) REFERENCES component(id);
ALTER TABLE ONLY sourcepackagepublishing
    ADD CONSTRAINT sourcepackagepublishing_section_fk
    FOREIGN KEY (section) REFERENCES section(id);

