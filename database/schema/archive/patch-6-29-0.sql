set client_min_messages = ERROR;

ALTER TABLE POTemplate ADD sourcepackagerelease integer
    CONSTRAINT potemplate_sourcepackagerelease_fk 
    REFERENCES sourcepackagerelease(id);
ALTER TABLE POTemplate ADD sourcepackageversion text;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=29, patch=0;
