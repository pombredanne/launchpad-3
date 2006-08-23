SET client_min_messages=ERROR;

ALTER TABLE Project ADD COLUMN bugtracker
    INTEGER REFERENCES Bugtracker(id);

UPDATE Project SET bugtracker = ProjectBugTracker.bugtracker
    FROM ProjectBugTracker
    WHERE Project.id = ProjectBugTracker.project;

DROP TABLE ProjectBugtracker;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
