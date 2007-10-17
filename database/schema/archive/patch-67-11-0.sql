SET client_min_messages=ERROR;

CREATE TABLE NameBlacklist (
    id serial PRIMARY KEY,
    regexp text NOT NULL
        CONSTRAINT valid_regexp CHECK (valid_regexp(regexp)),
    comment text,
    CONSTRAINT nameblacklist__regexp__key UNIQUE (regexp)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 11, 0);
