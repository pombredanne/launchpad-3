
INSERT INTO Person (name, displayname, teamowner, teamdescription) VALUES (
    'rosetta-admins', 'Rosetta Administrators',
    (SELECT id FROM Person WHERE name='admins'),
    'Rosetta Administrators'
    );

INSERT INTO Person (name, displayname, teamowner, teamdescription) VALUES (
    'ubuntu-translators', 'Ubuntu Translators',
    (SELECT id FROM Person WHERE name='rosetta-admins'),
    'Ubuntu Translators'
    );

INSERT INTO TeamMembership (person, team, status) VALUES (
    (SELECT id FROM Person WHERE name='daf'),
    (SELECT id FROM Person WHERE name='rosetta-admins'),
    3
    );

INSERT INTO TeamMembership (person, team, status) VALUES (
    (SELECT id FROM Person WHERE name='carlos'),
    (SELECT id FROM Person WHERE name='rosetta-admins'),
    3
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='rosetta-admins'),
    (SELECT id FROM Person WHERE name='daf')
    );

INSERT INTO TeamParticipation (team, person) VALUES (
    (SELECT id FROM Person WHERE name='rosetta-admins'),
    (SELECT id FROM Person WHERE name='carlos')
    );

