INSERT INTO person (displayname, "password", name)
  VALUES ('Bugzilla Importer', NULL, 'bugzilla-importer');

INSERT INTO emailaddress (email, person, status)
  VALUES ('bugzilla-importer@launchpad.net',
          (SELECT id FROM person WHERE name = 'bugzilla-importer'), 4);
