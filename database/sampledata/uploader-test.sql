-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

-- Autotest distrorelease
INSERT INTO Distrorelease (name, title, description, distribution, version,
            summary, datereleased, releasestatus, parentrelease,
            owner, displayname)
	VALUES ('breezy-autotest', 'Breezy Badger Autotest',
	'Autotest version of Breezy',
	(SELECT id FROM Distribution WHERE name = 'ubuntu'),
	'6.6.6', 'Autosync uploader test',
	'2005-12-01 10:00:00', 1,
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	(SELECT id FROM Person WHERE name = 'mark'),
        'Breezy Badger Autotest');

-- distroarchrelease for i386
INSERT INTO Distroarchrelease (distrorelease, processorfamily,
                               architecturetag, owner, official)
            VALUES (
            (SELECT id FROM Distrorelease WHERE name = 'breezy-autotest'),
            (SELECT id FROM ProcessorFamily WHERE name = 'x86')
            'i386',
            (SELECT id FROM Person WHERE name = 'mark'),
            true);

-- section selection
INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'admin'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'base'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'comm'));

INSERT INTO SectionSelection (distrorelease, section)
         VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'debian-installer'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'devel'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'doc'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'editors'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'games'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'gnome'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'graphics'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'interpreters'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'kde'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'libdevel'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'libs'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'mail'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'math'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'misc'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'net'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'news'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'oldlibs'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'otherosfs'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'perl'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'python'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'shells'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'sound'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'tex'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'text'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'utils'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'web'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'x11'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'electronics'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'embedded'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'hamradio'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'science'));

INSERT INTO SectionSelection (distrorelease, section)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Section where name = 'translations'));

-- component selection
INSERT INTO ComponentSelection (distrorelease, component)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Component where name = 'main'));

INSERT INTO ComponentSelection (distrorelease, component)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Component where name = 'restricted'));

INSERT INTO ComponentSelection (distrorelease, component)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Component where name = 'universe'));

INSERT INTO ComponentSelection (distrorelease, component)
            VALUES(
              (SELECT id from distrorelease where name='breezy-autotest'),
              (SELECT id from Component where name = 'multiverse'));

-- Grant upload permission for 'Uploader-Test Team' members
INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu') ,
           	    (SELECT id from Component where name = 'main'),
                    (SELECT id from Person where name = 'ubuntu-team'));

INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu'),
           	    (SELECT id from Component where name = 'restricted'),
                    (SELECT id from Person where name = 'ubuntu-team'));

INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu'),
           	    (SELECT id from Component where name = 'universe'),
                    (SELECT id from Person where name = 'ubuntu-team'));

INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu'),
           	    (SELECT id from Component where name = 'multiverse'),
                    (SELECT id from Person where name = 'ubuntu-team'));

-- Lucille Config for Ubuntu distribution
UPDATE distribution set lucilleconfig = '[publishing]
pendingremovalduration=5
root=/var/tmp/archive
archiveroot=/var/tmp/archive/ubuntu
poolroot=/var/tmp/archive/ubuntu/pool
distsroot=/var/tmp/archive/ubuntu/dists
overrideroot=/var/tmp/archive/ubuntu-overrides
cacheroot=/var/tmp/archive/ubuntu-cache
miscroot=/var/tmp/archive/ubuntu-misc
' WHERE name = 'ubuntu';

-- Lucille Config for Ubuntu Distroreleases
UPDATE distrorelease set lucilleconfig = '[publishing]
components = main restricted universe multiverse
' WHERE name = 'breezy-autotest';

UPDATE distrorelease set lucilleconfig = '[publishing]
components = main restricted universe multiverse
' WHERE name = 'warty';

UPDATE distrorelease set lucilleconfig = '[publishing]
components = main restricted universe multiverse
' WHERE name = 'hoary';

UPDATE distrorelease set lucilleconfig = '[publishing]
components = main restricted universe multiverse
' WHERE name = 'grumpy';
