/*
 * Lots of bits needed for Soyuz1.0
 */

SET client_min_messages=ERROR;

-- package publishing needs a view which won't contain embargoed packages

CREATE OR REPLACE VIEW SourcePackagePublishingPublicHistory AS
    SELECT * FROM SourcePackagePublishingHistory WHERE embargo = FALSE;

CREATE OR REPLACE VIEW PackagePublishingPublicHistory AS
    SELECT * FROM PackagePublishingHistory WHERE embargo = FALSE;
    
-- We need to know if a builder is a 'SECURITY' builder or not

ALTER TABLE Builder ADD COLUMN trusted BOOLEAN;
ALTER TABLE Builder ALTER COLUMN trusted SET DEFAULT FALSE;
UPDATE Builder SET trusted=FALSE;
ALTER TABLE Builder ALTER COLUMN trusted SET NOT NULL;

-- We would prefer to identify builders by their URL rather than their FQDN

ALTER TABLE Builder ADD COLUMN url TEXT;
UPDATE Builder SET url = 'http://' || fqdn || ':8221/';
ALTER TABLE Builder ALTER COLUMN url SET NOT NULL;
ALTER TABLE Builder DROP COLUMN fqdn;
ALTER TABLE Builder ADD CONSTRAINT builder_url_key UNIQUE(url);
ALTER TABLE Builder ADD CONSTRAINT valid_absolute_url
    CHECK (valid_absolute_url(url));

-- Now that we have pockets, a simple chroot column on distroarchrelease is
-- not enough. instead we have to have a chroots table...

CREATE TABLE PocketChroot (
	id SERIAL PRIMARY KEY,
	distroarchrelease INTEGER REFERENCES distroarchrelease(id),
	pocket INTEGER NOT NULL, -- dbschema.PackagePublishingPocket
	chroot INTEGER  REFERENCES libraryfilealias(id),
	
	UNIQUE(distroarchrelease,pocket),
	UNIQUE(chroot)
	);

INSERT INTO PocketChroot (distroarchrelease,pocket,chroot)
    SELECT id,0,chroot FROM distroarchrelease;

ALTER TABLE distroarchrelease DROP COLUMN chroot;

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 14, 0);
