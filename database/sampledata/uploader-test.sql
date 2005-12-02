
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
	(SELECT id FROM Person WHERE name = 'sabdfl'), 
        'Breezy Badger Autotest');

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

-- Grant upload permission for 'Uploader-Test Team' members
INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu') ,
           	    (SELECT id from Component where name = 'main'),
                    (SELECT id from Person where name = 'name17'));  

INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu'),
           	    (SELECT id from Component where name = 'restricted'),
                    (SELECT id from Person where name = 'name17'));  

INSERT INTO DistroComponentUploader (distribution, component, uploader)
            VALUES ((SELECT id from Distribution where name = 'ubuntu'), 
           	    (SELECT id from Component where name = 'universe'),
                    (SELECT id from Person where name = 'name17'));  


