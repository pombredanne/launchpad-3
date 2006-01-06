
set client_min_messages=ERROR;

/* move the needs_discussion flag from SprintSpecification to Specification
 */

ALTER TABLE Specification ADD COLUMN needs_discussion boolean;
UPDATE Specification SET needs_discussion = TRUE;
UPDATE Specification SET needs_discussion = FALSE FROM
    SprintSpecification WHERE
    Specification.id = SprintSpecification.sprint AND
    SprintSpecification.needs_discussion = FALSE;
ALTER TABLE Specification ALTER COLUMN needs_discussion SET DEFAULT TRUE;
ALTER TABLE Specification ALTER COLUMN needs_discussion SET NOT NULL;

ALTER TABLE SprintSpecification DROP COLUMN needs_discussion;

/* add a direction_approved flag */

ALTER TABLE Specification ADD COLUMN direction_approved boolean;
UPDATE Specification SET direction_approved = TRUE;
UPDATE Specification SET direction_approved = FALSE
    WHERE status > 10 AND status < 50;
ALTER TABLE Specification ALTER COLUMN direction_approved SET DEFAULT FALSE;
ALTER TABLE Specification ALTER COLUMN direction_approved SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,51,0);

