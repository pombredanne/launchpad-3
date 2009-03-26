SET client_min_messages=ERROR;

-- User defined PPA displayname.
ALTER TABLE Archive ADD COLUMN displayname text;

-- Public PPAs.
UPDATE Archive SET displayname = ('PPA for ' || p.displayname)
    FROM person p  WHERE
    archive.owner=p.id AND archive.purpose=2 AND archive.private=false;

-- Private PPAs.
UPDATE Archive SET displayname = ('Private PPA for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=2 AND archive.private=true;

-- Public Copy archives.
UPDATE Archive SET displayname = (
    'Copy archive ' || archive.name || ' for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=6 AND archive.private=false;

-- Private Copy archives.
UPDATE Archive SET displayname = (
    'Private copy archive ' || archive.name || ' for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=6 AND archive.private=true;

-- Primary archives.
UPDATE Archive SET displayname = ('Primary Archive for ' || d.title)
    FROM distribution d WHERE
    archive.distribution=d.id AND archive.purpose=1;

-- Partner archives.
UPDATE Archive SET displayname = ('Partner Archive for ' || d.title)
    FROM distribution d WHERE
    archive.distribution=d.id AND archive.purpose=4;

-- All set, make displayname NOT NULL.
ALTER TABLE Archive ALTER COLUMN displayname SET NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 43, 0);
