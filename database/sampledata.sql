/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.  This requires the default
   data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('schema', 'SCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('trema', 'XCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('enema', 'ENHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);

-- Distribution
INSERT INTO Distribution (name, title, description, owner) values ('Ubuntu', 'Ubuntu Distribution', 'text ...', 1);
INSERT INTO Distribution (name, title, description, owner) values ('Redhat', 'Redhat Advanced Server', 'some text', 1);
INSERT INTO Distribution (name, title, description, owner) values ('Debian', 'Debian Crazy-Unstable', 'text ...', 1);
INSERT INTO Distribution (name, title, description, owner) values ('Gentoo', 'The Gentoo bits', 'another ...', 1);
INSERT INTO Distribution (name, title, description, owner) values ('Porky Pig Polka', 'Swine-oriented Distribution', 'blabla', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate) values ('Warty', 'The First Distribution', 'text ...', 1, 'PONG', 1, 1, 0);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate) values ('6.0', 'Six Six Six', 'some text', 2, '12321.XX', 1, 1, 0);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate) values ('Hoary', 'Hoary Crazy-Unstable', 'text ...', 1, 'EWEpp##', 1, 1, 0);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate) values ('7.0', 'Seven', 'another ...', 2, 'ACK ACK', 1, 1, 0);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate) values ('Grumpy', 'G-R-U-M-P-Y', 'blabla', 1, 'PINKPY POLLY', 1, 1, 0);


-- Binarypackage
INSERT INTO Binarypackage (name, title, description) values ('mozilla-firefox-0.8', 'Mozilla Firefox', 'some text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-thunderbird-1.5', 'Mozilla Thunderbird', 'text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-browser-1.4', 'Mozilla Browser', 'text and so');
INSERT INTO Binarypackage (name, title, description) values ('emacs21-1.6', 'Emacs21 Programming Editor', 'fofofof');
INSERT INTO Binarypackage (name, title, description) values ('bash-1.8', 'Bash', 'another data');
