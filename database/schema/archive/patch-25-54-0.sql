/*
 * Remove the components and sections column from DistroRelease
 */

SET client_min_messages = ERROR;

ALTER TABLE DistroRelease DROP COLUMN Components;
ALTER TABLE DistroRelease DROP COLUMN Sections;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,54,0);
