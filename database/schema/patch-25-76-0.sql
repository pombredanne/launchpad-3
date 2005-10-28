
set client_min_messages=ERROR;

/* add ability to know which spec superseded a current spec */

ALTER TABLE Specification ADD COLUMN superseded_by integer;
ALTER TABLE Specification ADD CONSTRAINT specification_superseded_by_fk
    FOREIGN KEY (superseded_by) REFERENCES Specification(id);
ALTER TABLE Specification ADD CONSTRAINT specification_not_self_superseding
    CHECK (superseded_by <> id);

/* improve our ability to track proposals of specs for sprints */

ALTER TABLE SprintSpecification ADD COLUMN whiteboard text;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,76,0);
