/* NOT NULL removals for Carlos */
ALTER TABLE POTemplate ALTER priority DROP NOT NULL;
ALTER TABLE POTemplate ALTER branch DROP NOT NULL;
ALTER TABLE POTemplate ALTER description DROP NOT NULL;
ALTER TABLE POTemplate ALTER copyright DROP NOT NULL;
ALTER TABLE POTemplate ALTER license DROP NOT NULL;
ALTER TABLE POTemplate ALTER path DROP NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=8, patch=0;

