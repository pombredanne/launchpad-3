SET client_min_messages TO ERROR;

/* Fix for Carlos */
ALTER TABLE pomsgidsighting DROP CONSTRAINT pomsgidsighting_potmsgset_key;

/*
  Add a bugtrackertype for debbugs, and the debbugs system itself
*/

/* This data will sneak into the sampledata, so silence insert errors */
SET client_min_messages TO FATAL;
INSERT INTO BugTrackerType (name, title, description, homepage, owner) VALUES 
    ( 'debbugs', 'Debbugs System', 'Debbugs Bug Tracking System', 'http://bugs.debian.org/', 1 );
INSERT INTO Bugtracker ( bugtrackertype, name, title, shortdesc, baseurl, owner ) VALUES
    ( (SELECT id FROM BugTrackerType WHERE name='debbugs'), 'debbugs', 'Debian Bug tracker', 'Bug tracker for debian project.', 'http://bugs.debian.org', 1);
SET client_min_messages TO ERROR;

DELETE FROM LaunchpadDatabaseRevision;
INSERT INTO  LaunchpadDatabaseRevision VALUES (4, 9, 0);

