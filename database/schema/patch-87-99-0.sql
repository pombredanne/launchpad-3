-- New column: "don't accept PO imports for this release just now"
ALTER TABLE distrorelease
ADD COLUMN defer_translation_imports boolean NOT NULL DEFAULT false;

INSERT INTO LaunchpadDatabaseRevision VALUES(87, 99, 0);

