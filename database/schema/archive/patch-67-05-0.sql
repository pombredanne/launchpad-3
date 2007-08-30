SET client_min_messages=ERROR;

CREATE TABLE BugTag (
    id SERIAL PRIMARY KEY,
    bug INTEGER NOT NULL,
    tag TEXT NOT NULL,
    CONSTRAINT valid_tag CHECK (valid_name(tag)),
    CONSTRAINT bugtag__tag__bug__key UNIQUE (tag, bug)
    );

CREATE INDEX bugtag__bug__idx ON BugTag(bug);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 05, 0);

