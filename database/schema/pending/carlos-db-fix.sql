ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 2)) OR (rawfile IS NOT NULL));

ALTER TABLE POFile DROP CONSTRAINT pofile_rawimportstatus_valid;
ALTER TABLE POFile ADD CONSTRAINT pofile_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 2)) OR (rawfile IS NOT NULL));
