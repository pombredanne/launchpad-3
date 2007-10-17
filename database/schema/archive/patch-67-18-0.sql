SET client_min_messages=ERROR;

ALTER TABLE Project ADD COLUMN bugtracker
    INTEGER REFERENCES Bugtracker(id);

UPDATE Project SET bugtracker = ProjectBugTracker.bugtracker
    FROM ProjectBugTracker
    WHERE Project.id = ProjectBugTracker.project;

DROP TABLE ProjectBugtracker;

ALTER TABLE Product ADD COLUMN bugtracker
    INTEGER REFERENCES Bugtracker(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 18, 0);
