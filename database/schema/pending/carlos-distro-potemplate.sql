ALTER TABLE POTemplate ADD sourcepackagename integer REFERENCES SourcePackageName(id);
ALTER TABLE POTemplate ADD distrorelease integer REFERENCES DistroRelease(id);

COMMENT ON COLUMN POTemplate.sourcepackagename IS 'A reference to a sourcepackage name from where this POTemplate comes.';
COMMENT ON COLUMN POTemplate.distrorelease IS 'A reference to the distribution from where this POTemplate comes.';
