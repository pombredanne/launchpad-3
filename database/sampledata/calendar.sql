
INSERT INTO Calendar (owner, title, revision)
    VALUES (16, 'Foo Calendar', 0);
UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Foo Calendar') WHERE id = 16;
