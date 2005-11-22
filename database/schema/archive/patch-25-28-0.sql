set client_min_messages=ERROR;

-- Rename ManifestEntry patchon column to parent
-- this makes it match the hct code and reflects that this is used
-- for more than just patches

-- Add the new column
ALTER TABLE ManifestEntry ADD COLUMN parent integer;
ALTER TABLE ManifestEntry ADD CONSTRAINT
	manifestentry_parent_paradox CHECK ((parent <> "sequence"));
ALTER TABLE ManifestEntry ADD CONSTRAINT
	manifestentry_parent_related
		FOREIGN KEY (manifest, parent)
		REFERENCES ManifestEntry(manifest, "sequence");

-- Copy across the data
UPDATE ManifestEntry SET parent=patchon;

-- Drop the old column
ALTER TABLE ManifestEntry DROP COLUMN patchon;


INSERT INTO LaunchpadDatabaseRevision VALUES (25, 28, 0);
