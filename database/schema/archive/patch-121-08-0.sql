SET client_min_messages=ERROR;

CREATE TABLE ArchiveDependency (
    id serial PRIMARY KEY,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    archive integer NOT NULL REFERENCES Archive(id),
    dependency integer NOT NULL REFERENCES Archive(id),
    CONSTRAINT distinct_archives CHECK (archive != dependency),
    CONSTRAINT archivedependency_unique UNIQUE (archive, dependency)
);

CREATE INDEX archivedependency__archive__idx ON archivedependency
     USING btree (archive);
CREATE INDEX archivedependency__dependency__idx ON archivedependency
     USING btree (dependency);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 08, 0);
