SET client_min_messages TO error;

/* Ensure a bug is not a duplicate of itself */
ALTER TABLE Bug ADD CHECK (not id = duplicateof);

/* 
    Add an 'assignee' to a productbugassignment 
    and a sourcepackagebugassignment
 */
ALTER TABLE ProductBugAssignment ADD assignee integer REFERENCES Person(id);
ALTER TABLE ProductBugAssignment ALTER COLUMN assignee SET NOT NULL;

ALTER TABLE SourcePackageBugAssignment ADD assignee integer 
    REFERENCES Person(id);
ALTER TABLE SourcePackageBugAssignment ALTER COLUMN assignee SET NOT NULL;

/* DistroRelease name unique */
ALTER TABLE Distribution ADD UNIQUE (name);
ALTER TABLE DistroRelease ADD UNIQUE (distribution, name);

/* Names must be lower case */
ALTER TABLE DistroRelease ADD CHECK (name = lower(name));
ALTER TABLE Distribution ADD CHECK (name = lower(name));

