SET client_min_messages TO error;

/* More bugsystem -> bugtracker renaming */

ALTER TABLE BugSystemType RENAME TO BugTrackerType;
ALTER TABLE BugWatch RENAME COLUMN bugsystem TO bugtracker;

