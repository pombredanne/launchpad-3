SET client_min_messages=ERROR;

-- User defined PPA title.
ALTER TABLE Archive ADD COLUMN title text;

-- Public PPAs.
UPDATE Archive SET title = ('PPA for ' || p.displayname)
    FROM person p  WHERE
    archive.owner=p.id AND archive.purpose=2 AND archive.private=false;

-- Private PPAs.
UPDATE Archive SET title = ('Private PPA for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=2 AND archive.private=true;

-- Public Copy archives.
UPDATE Archive SET title = (
    'Copy archive ' || archive.name || ' for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=6 AND archive.private=false;

-- Private Copy archives.
UPDATE Archive SET title = (
    'Private copy archive ' || archive.name || ' for ' || p.displayname)
    FROM person p WHERE
    archive.owner=p.id AND archive.purpose=6 AND archive.private=true;

-- Primary archives.
UPDATE Archive SET title = ('Primary Archive for ' || d.title)
    FROM distribution d WHERE
    archive.distribution=d.id AND archive.purpose=1;

-- Partner archives.
UPDATE Archive SET title = ('Partner Archive for ' || d.title)
    FROM distribution d WHERE
    archive.distribution=d.id AND archive.purpose=4;

-- All set, make title NOT NULL.
ALTER TABLE Archive ALTER COLUMN title SET NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
