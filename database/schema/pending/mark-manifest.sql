
/*
  We are starting to make Sourcerer talk to the db, and these tweaks are required
  to make it work properly.
*/

ALTER TABLE ManifestEntry ALTER COLUMN branch DROP NOT NULL;

ALTER TABLE Manifest ADD COLUMN uuid TEXT;

-- set the uuid's to be text versions of the id
UPDATE Manifest SET uuid = text(id);

ALTER TABLE Manifest ALTER COLUMN uuid SET NOT NULL;
ALTER TABLE Manifest 
    ADD CONSTRAINT "manifest_uuid_uniq"
            UNIQUE(uuid);

