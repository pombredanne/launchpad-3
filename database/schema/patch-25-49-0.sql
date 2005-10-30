
set client_min_messages=ERROR;

/* add ability to know which spec superseded a current spec */

ALTER TABLE Specification ADD COLUMN superseded_by integer;
ALTER TABLE Specification ADD CONSTRAINT specification_superseded_by_fk
    FOREIGN KEY (superseded_by) REFERENCES Specification(id);
ALTER TABLE Specification ADD CONSTRAINT specification_not_self_superseding
    CHECK (superseded_by <> id);

/* improve our ability to track proposals of specs for sprints */

ALTER TABLE SprintSpecification ADD COLUMN whiteboard text;

/* dealing with a NULL priority is just a pain in the nexk that results in
 * unnecessarily complicated TAL. */

UPDATE Specification SET priority=5 WHERE priority IS NULL;
ALTER TABLE Specification ALTER COLUMN priority SET DEFAULT 5;
ALTER TABLE Specification ALTER COLUMN priority SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,49,0);

