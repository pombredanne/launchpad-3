
CREATE TABLE PackageSelection (
    distrorelease int references DistroRelease,
    sourcepackagename int references SourcePackageName,
    binarypackagename


ALTER TABLE Maintainership
    - distrorelease
    - sourcepackagename
    - person

ALTER TABLE Packaging
    - distr
    - sourcepackagename
    - product
    - nature

ALTER TABLE HeadManifest
    - distrorelease
    - manifest
    - sourcepackagename
    - person

ALTER TABLE SourceSource

ALTER TABLE  SourcepackageRelease
    - sourcepackageformat
    - distrorelease

ALTER TABLE DistroRelease
    - current boolean
    - primaryarchitecture
    - inert (just another state in distributionreleasestate ?)

ALTER TABLE Distribution
    - project NOT NULL


DROP TABLE SourcepackageBugAssignment;

DROP TABLE SourcePackageRelationship (pending Scott approval);



