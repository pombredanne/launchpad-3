
set client_min_messages=ERROR;

ALTER TABLE SprintSpecification ADD COLUMN status integer;
UPDATE SprintSpecification SET status=30 WHERE status IS NULL;
ALTER TABLE SprintSpecification ALTER COLUMN status SET DEFAULT 30;
ALTER TABLE SprintSpecification ALTER COLUMN status SET NOT NULL;

ALTER TABLE SprintSpecification ADD COLUMN needs_discussion boolean;
UPDATE SprintSpecification SET needs_discussion = TRUE
    WHERE needs_discussion IS NULL;
ALTER TABLE SprintSpecification ALTER COLUMN needs_discussion SET NOT NULL;
ALTER TABLE SprintSpecification ALTER COLUMN needs_discussion SET DEFAULT TRUE;

ALTER TABLE Specification ALTER COLUMN priority DROP NOT NULL;
UPDATE Specification SET priority = NULL WHERE priority = 50;

ALTER TABLE DistroArchRelease ADD COLUMN package_count integer;
UPDATE DistroArchRelease SET package_count = 0 WHERE package_count IS NULL;
ALTER TABLE DistroArchRelease ALTER COLUMN package_count SET DEFAULT 0;
ALTER TABLE DistroArchRelease ALTER COLUMN package_count SET NOT NULL;

ALTER TABLE DistroRelease ADD COLUMN binarycount integer;
UPDATE DistroRelease SET binarycount = 0 WHERE binarycount IS NULL;
ALTER TABLE DistroRelease ALTER COLUMN binarycount SET DEFAULT 0;
ALTER TABLE DistroRelease ALTER COLUMN binarycount SET NOT NULL;

ALTER TABLE DistroRelease ADD COLUMN sourcecount integer;
UPDATE DistroRelease SET sourcecount = 0 WHERE sourcecount IS NULL;
ALTER TABLE DistroRelease ALTER COLUMN sourcecount SET DEFAULT 0;
ALTER TABLE DistroRelease ALTER COLUMN sourcecount SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,45,0);

