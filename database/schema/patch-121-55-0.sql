SET client_min_messages=ERROR;

-- This (new) link table ties a "rebuild archive" to a DistroSeries,
-- captures the rebild life cycle data and statistics.
CREATE TABLE archiverebuild (
    id serial PRIMARY KEY,
    -- This is the archive to be used for the rebuild.
    archive integer NOT NULL,
    -- This is the DistroSeries in question.
    distroseries integer NOT NULL,
    -- The person who requested/started the rebuild.
    registrant integer NOT NULL,
    -- The rebuild status (in-progress, complete, cancelled, obsolete).
    status integer NOT NULL,
    -- The reason why this rebuild was started (one-liner).
    reason text,
    -- When was this rebuild requested?
    date_created timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL
);

-- A "rebuild archive" may be used only once i.e. for a single DistroSeries.
ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__archive__key UNIQUE (archive);

ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__archive__fk FOREIGN KEY (archive) REFERENCES archive(id);

ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__distroseries__fk FOREIGN KEY (distroseries) REFERENCES distroseries(id);

ALTER TABLE ONLY archiverebuild
    ADD CONSTRAINT archiverebuild__requestor__fk FOREIGN KEY (registrant) REFERENCES person(id);

CREATE INDEX archiverebuild__registrant__idx ON archiverebuild USING btree (registrant);

-- When were the rebuild statistics last updated?
ALTER TABLE archive ADD COLUMN
    date_updated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL;
-- How many source packages are in the rebuild archive altogether?
ALTER TABLE archive ADD COLUMN
    total_count integer NOT NULL Default 0;
-- How many packages still need building?
ALTER TABLE archive ADD COLUMN
    pending_count integer NOT NULL Default 0;
-- How many source packages were build sucessfully?
ALTER TABLE archive ADD COLUMN
    succeeded_count integer NOT NULL Default 0;
-- How many packages failed to build?
ALTER TABLE archive ADD COLUMN
    failed_count integer NOT NULL Default 0;
-- How many packages are building at present?
ALTER TABLE archive ADD COLUMN
    building_count integer NOT NULL Default 0;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 55, 0);
