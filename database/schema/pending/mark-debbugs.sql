
/*
  Add a bugtrackertype for debbugs, and the debbugs system itself
*/

INSERT INTO BugTrackerType (name, title, description, homepage, owner) VALUES 
    ( 'debbugs', 'Debbugs System', 'Debbugs Bug Tracking System', 'http://bugs.debian.org/', 1 );


INSERT INTO Bugtracker ( bugtrackertype, name, title, shortdesc, baseurl, owner ) VALUES
    ( (SELECT id FROM BugTrackerType WHERE name='debbugs'), 'debbugs', 'Debian Bug tracker', 'Bug tracker for debian project.', 'http://bugs.debian.org', 1);


