SET client_min_messages=ERROR;

CREATE TABLE BugTrackerAlias (
       id SERIAL PRIMARY KEY,
       bugtracker INTEGER NOT NULL,
       baseurl TEXT NOT NULL,
       CONSTRAINT bugtrackeralias__bugtracker__fk
                  FOREIGN KEY (bugtracker)
                  REFERENCES BugTracker,
       CONSTRAINT bugtracker__baseurl__key
                  UNIQUE (baseurl)
       );

CREATE INDEX bugtrackeralias__bugtracker__idx
       ON BugTrackerAlias(bugtracker);

INSERT INTO LaunchpadDatabaseRevision
       VALUES (88, 99, 0);
