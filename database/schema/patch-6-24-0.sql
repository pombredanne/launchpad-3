SET client_min_messages TO ERROR;

ALTER TABLE POTemplate ADD sourcepackagename integer
    CONSTRAINT potemplate_sourcepackagename_fk REFERENCES SourcePackageName(id);
ALTER TABLE POTemplate ADD distrorelease integer
    CONSTRAINT potemplate_distrorelease_fk REFERENCES DistroRelease(id);

/*
Don't know if these are needed yet

CREATE INDEX potemplate_sourcepackagename_idx ON POTemplate(sourcepackagename);
CREATE INDEX potemplate_distrorelease_idx ON POTemplate(distrorelease);
*/

UPDATE LaunchpadDatabaseRevision SET major=6, minor=24, patch=0;

