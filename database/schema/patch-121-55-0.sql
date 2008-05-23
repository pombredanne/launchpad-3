SET client_min_messages=ERROR;

-- This (new) link table ties a "rebuild archive" to a DistroSeries.
CREATE TABLE archiverebuild (
    id serial PRIMARY KEY,
    -- This is the "rebuild archive" in question.
    archive integer NOT NULL,
    -- This is the DistroSeries in question.
    distroseries integer NOT NULL
);

-- A "rebuild archive" may be used only once i.e. for a single DistroSeries.
ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__archive__key UNIQUE (archive);

ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 55, 0);
