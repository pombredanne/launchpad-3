SET client_min_messages TO error;

ALTER TABLE BugSystem RENAME TO BugTracker;
ALTER TABLE BugTracker RENAME COLUMN bugsystemtype TO bugtrackertype;

CREATE UNIQUE INDEX bugtracker_name_key ON BugTracker(name);
ALTER TABLE BugTracker ADD CHECK (name = lower(name));

