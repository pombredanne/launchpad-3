

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


CREATE TABLE PackageSelection (
    distrorelease int references DistroRelease,
    sourcepackagename int references SourcePackageName,
    binarypackagename

/* Derivative Distribution */

CREATE TABLE PackageSelection (
    distrorelease int references DistroRelease NOT NULL,
    sourcepackagename int references sourcepackagename NOT NULL,
    binarypackagename int references binarypackagename,
    component int references component,
    section int references section,
    priority int
);

/* Inheritance policy for PackageSelecction
    If a column is NULL, inherit from parent release, parents parent release
    etc. If all else fails, inherit from the sourcepackagerelease as
    determined by the distrorelease and the sourcepackagename
*/

ALTER TABLE DistroRelease ADD COLUMN inheritancetype int; /* dbschema */

/* DistroRelease.releasestate needs to be extended to allow states required
by the Distribution Derivation Workflow (see DerivationOverview) */

/* We need this column to let s determine what distro a given sourcepackage
   was uploaded to, which is imported for overlay distributions */
ALTER TABLE SourcePackageRelease ADD COLUMN distrorelease int references
    distrorelease;

/* This column tells us if seeds for this DistroRelease should be inherited
   from the parent distrorelease */
ALTER TABLE DistroRelease ADD COLUMN inheritseeds boolean;

ALTER TABLE Distribution ADD COLUMN currentrelease int references
    distrorelease;


