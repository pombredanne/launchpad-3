DROP TABLE BugInfestation;

CREATE TABLE LaunchpadDatabaseRevision (
    major int,
    minor int,
    patch int
    );

CREATE INDEX sourcepackage_maintainer_key on Sourcepackage (maintainer);

ALTER TABLE SourcepackageRelease DROP CONSTRAINT "$4";
ALTER TABLE SourcepackageRelease 
    ADD CONSTRAINT sourcepackagerelease_component_fk 
    FOREIGN KEY (component) REFERENCES Component(id);

