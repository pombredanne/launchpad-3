ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POTemplate ALTER rawimportstatus SET DEFAULT 0;

ALTER TABLE POFile DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 1)) OR (rawfile IS NOT NULL));
ALTER TABLE POFile ALTER rawimportstatus SET DEFAULT 0;

