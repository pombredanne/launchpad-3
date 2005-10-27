set client_min_messages=ERROR;

/*
 * Add to the Distribution and DistroRelease some useful addresses
 */

ALTER TABLE Distribution ADD COLUMN uploadsender TEXT;
ALTER TABLE Distribution ADD COLUMN uploadadmin TEXT;
ALTER TABLE DistroRelease ADD COLUMN changeslist TEXT;

/*
 * DistroComponentUploader is to control the upload permissions for
 * launchpad.
 */

CREATE TABLE DistroComponentUploader (
	id           SERIAL  NOT NULL 
	             PRIMARY KEY,
	distribution integer NOT NULL 
		     CONSTRAINT distrocomponentuploader_distribution_fk 
	             REFERENCES Distribution(id),
	component    integer NOT NULL
	             CONSTRAINT distrocomponentuploader_component_fk
		     REFERENCES Component(id),
	uploader     integer NOT NULL
	             CONSTRAINT distrocomponentuploader_uploader_fk
		     REFERENCES Person(id)
	);

ALTER TABLE DistroComponentUploader
    ADD CONSTRAINT distrocomponentuploader_distro_component_uniq
    UNIQUE (distribution, component);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,39,0);
