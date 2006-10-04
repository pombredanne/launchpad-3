
BEGIN;

-- Create the tracker row for collapsed SourceForge tracker instance.
-- Bugtracker type "5" is SOURCEFORGE.

INSERT INTO bugtracker (bugtrackertype, name, title, summary, baseurl, owner)
  VALUES (
    5,
    'sf',
    'SourceForge.net Tracker',
    'SourceForge.net is an Open Source software development web site, hosting more than 100,000 projects.  This is the tracker used by most of those projects.',
    'http://sourceforge.net/',
    (SELECT id FROM person WHERE name = 'registry'));

-- Move bug watches to new tracker
UPDATE bugwatch
  SET bugtracker = (SELECT id FROM bugtracker WHERE name = 'sf')
  WHERE bugtracker IN (SELECT id FROM bugtracker WHERE bugtrackertype = 5);

-- Move project bugtracker links
UPDATE project
  SET bugtracker = (SELECT id FROM bugtracker WHERE name = 'sf')
  WHERE bugtracker IN (SELECT id FROM bugtracker WHERE bugtrackertype = 5);

-- Move product bugtracker links
UPDATE product
  SET bugtracker = (SELECT id FROM bugtracker WHERE name = 'sf')
  WHERE bugtracker IN (SELECT id FROM bugtracker WHERE bugtrackertype = 5);

-- Remove unneeded bugtrackers
DELETE FROM bugtracker WHERE bugtrackertype = 5 AND name <> 'sf';

COMMIT;
