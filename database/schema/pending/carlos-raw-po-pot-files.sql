ALTER TABLE POTemplate ADD rawfile text;
ALTER TABLE POTemplate ADD rawimporter integer REFERENCES Person(id);
ALTER TABLE POTemplate ADD daterawimport timestamp without time zone;
ALTER TABLE POTemplate ADD rawimportstatus integer;
ALTER TABLE POTemplate ALTER daterawimport set default (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL)));

ALTER TABLE POFile ADD rawfile text;
ALTER TABLE POFile ADD rawimporter integer REFERENCES Person(id);
ALTER TABLE POFile ADD daterawimport timestamp without time zone;
ALTER TABLE POFile ADD rawimportstatus integer;
ALTER TABLE POFile ALTER daterawimport set default (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE POFile ADD CONSTRAINT potemplate_rawimportstatus_valid CHECK(((rawfile IS NULL) AND (rawimportstatus <> 0)) OR ((rawfile IS NOT NULL) AND (rawimportstatus IS NOT NULL)));

COMMENT ON TABLE POTemplate IS 'This table stores a pot file for a given product.';
COMMENT ON COLUMN POTemplate.rawfile IS 'The pot file itself in raw mode.';
COMMENT ON COLUMN POTemplate.rawimporter IS 'The person that attached the rawfile.';
COMMENT ON COLUMN POTemplate.daterawimport IS 'The date when the rawfile was attached.';
COMMENT ON COLUMN POTemplate.rawimportstatus IS 'The status of the import: 0 pending import, 1 imported, 2 failed.';

COMMENT ON TABLE POFile IS 'This table stores a po file for a given product.';
COMMENT ON COLUMN POFile.rawfile IS 'The pot file itself in raw mode.';
COMMENT ON COLUMN POFile.rawimporter IS 'The person that attached the rawfile.';
COMMENT ON COLUMN POFile.daterawimport IS 'The date when the rawfile was attached.';
COMMENT ON COLUMN POFile.rawimportstatus IS 'The status of the import: 0 pending import, 1 imported, 2 failed.';

