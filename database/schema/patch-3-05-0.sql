ALTER TABLE ProductBugAssignment 
    ADD COLUMN dateassigned timestamp without time zone;
ALTER TABLE ProductBugAssignment ALTER COLUMN dateassigned 
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
UPDATE ProductBugAssignment
    SET dateassigned = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE dateassigned IS NULL;
ALTER TABLE ProductBugAssignment ALTER COLUMN dateassigned SET NOT NULL;

ALTER TABLE SourcePackageBugAssignment
    ADD COLUMN dateassigned timestamp without time zone;
ALTER TABLE SourcePackageBugAssignment ALTER COLUMN dateassigned 
    SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
UPDATE SourcePackageBugAssignment
    SET dateassigned = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE dateassigned IS NULL;
ALTER TABLE SourcePackageBugAssignment ALTER COLUMN dateassigned SET NOT NULL;

