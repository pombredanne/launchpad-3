-- New column: "don't accept PO imports for this release just now"
ALTER TABLE distrorelease
ADD COLUMN defer_translation_imports boolean NOT NULL DEFAULT true;
UPDATE distrorelease SET defer_translation_imports = false;

