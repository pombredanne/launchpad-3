/*

  CREATE SAMPLE PROJECTS AND PRODUCTS

*/
INSERT INTO Project (owner, name, displayname, title, shortdesc, 
description, homepageurl)
VALUES (
(SELECT id FROM Person WHERE displayname='Sample Person'),
'mozilla', 'The Mozilla Project', 'The Mozilla Project',
'The Mozilla Project is the largest open source web browser collaborative project.',
'The Mozilla Project is the largest open source web browser '
|| 'collaborative project. The Mozilla Project produces several internet '
|| 'applications that are very widely used, and is also a center for '
|| 'collaboration on internet standards work by open source groups.',
'http://www.mozilla.org/'
);

-- Mozilla Firefox
INSERT INTO Product (project, owner, name, displayname,  title, shortdesc,
description)
VALUES (
(SELECT id FROM Project WHERE name='mozilla'),
(SELECT id FROM Person WHERE displayname='Sample Person'),
'firefox', 'Mozilla Firefox', 'Mozilla Firefox',
'The Mozilla Firefox web browser',
'The Mozilla Firefox web browser'
);
INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES (
(SELECT id FROM Product WHERE name='firefox'),
timestamp '2004-06-28 00:00', 'mozilla-firefox-0.9.1',
(SELECT id FROM Person WHERE displayname='Sample Person')
);

INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Person WHERE displayname='Sample Person'),
	'gnome', 'GNOME', 'The GNOME Project', 'foo', 'bar', 'http://www.gnome.org/' );
INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Person WHERE displayname='Sample Person'),
	'iso-codes', 'iso-codes', 'iso-codes', 'foo', 'bar', 'http://www.gnome.org/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Project WHERE name='gnome'),
	(SELECT id FROM Person WHERE displayname='Sample Person'),
	'evolution', 'Evolution', 'The Evolution Groupware', 'foo', 'bar', 'http://www.novell.com/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Project WHERE name='gnome'),
	(SELECT id FROM Person WHERE displayname='Sample Person'),
	'gnome-terminal', 'GNOME Terminal', 'The GNOME terminal emulator', 'foo', 'bar', 'http://www.gnome.org/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Project WHERE name='iso-codes'),
	(SELECT id FROM Person WHERE displayname='Sample Person'),
	'iso-codes', 'iso-codes', 'The iso-codes', 'foo', 'bar', 'http://www.novell.com/' );

