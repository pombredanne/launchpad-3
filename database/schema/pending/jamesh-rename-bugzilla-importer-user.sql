BEGIN;

UPDATE Person
  SET name = 'bug-importer',
      displayname = 'Bug Importer'
  WHERE name = 'bugzilla-importer';

UPDATE EmailAddress
  SET email = 'bug-importer@launchpad.net'
  WHERE email = 'bugzilla-importer@launchpad.net';

END;
