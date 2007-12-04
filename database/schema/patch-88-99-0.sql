SET client_min_messages=ERROR;

CREATE TABLE BugTrackerAlias (
       id SERIAL PRIMARY KEY,
       bugtracker INTEGER NOT NULL,
       base_url TEXT NOT NULL,
       CONSTRAINT bugtrackeralias__bugtracker__fk
                  FOREIGN KEY (bugtracker)
                  REFERENCES BugTracker,
       CONSTRAINT bugtracker__base_url__key
                  UNIQUE (base_url)
       );

CREATE INDEX bugtrackeralias__bugtracker__idx
       ON BugTrackerAlias(bugtracker);

INSERT INTO LaunchpadDatabaseRevision
       VALUES (88, 99, 0);
