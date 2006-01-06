set client_min_messages=ERROR;

-- Add a new field to ManifestEntry
-- this will match dbschema.ManifestEntryHint
ALTER TABLE ManifestEntry ADD COLUMN hint integer;
ALTER TABLE ManifestEntry ADD CONSTRAINT
	manifest_hint_key UNIQUE (hint, manifest);

-- Add a new ManifestAncestry table
-- this will store the descent of manifests from each other
CREATE TABLE ManifestAncestry (
	id	serial NOT NULL PRIMARY KEY,
	parent	integer
		NOT NULL
		CONSTRAINT manifestancestry_parent_fk REFERENCES Manifest,
	child	integer
		NOT NULL
		CONSTRAINT manifestancestry_child_fk REFERENCES Manifest,

	-- Make sure we don't end up with loops
	CONSTRAINT manifestancestry_loops CHECK (parent != child),

	-- Make sure a pair is unique
	CONSTRAINT manifestancestry_pair_key UNIQUE (parent, child)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 16, 0);
