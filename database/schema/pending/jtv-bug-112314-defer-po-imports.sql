-- New column: "don't accept PO imports for this release just now"
ALTER TABLE distrorelease
ADD COLUMN defer_imports boolean NOT NULL DEFAULT false;

