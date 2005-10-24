
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

INSERT INTO LaunchpadDatabaseRevision VALUES (25,88,0);

