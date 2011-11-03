SET client_min_messages=ERROR;

/* POFileStatsJob holds scheduled jobs that are to update POFile statistics */
CREATE TABLE POFileStatsJob (
    id           SERIAL PRIMARY KEY,
    job          INTEGER NOT NULL UNIQUE REFERENCES Job(id),
    pofile       INTEGER NOT NULL UNIQUE REFERENCES POFile(id)
);

CREATE INDEX pofilestatsjob__job__idx ON Job(id);
CREATE INDEX pofilestatsjob__pofile__idx ON POFile(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 93, 0);
