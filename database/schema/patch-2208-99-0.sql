SET client_min_messages=ERROR;

CREATE TABLE DistroSeriesDifference (
    id serial PRIMARY KEY,
    derived_series integer CONSTRAINT distroseriesdifference__derived_series__fk REFERENCES distroseries,
    source_package_publishing_history integer CONSTRAINT distroseriesdifference__spph__fk REFERENCES sourcepackagepublishinghistory,
    parent_source_package_publishing_history integer CONSTRAINT distroseriesdifference__parent_spph__fk REFERENCES sourcepackagepublishinghistory,
    comment text,
    status integer NOT NULL
);
CREATE INDEX distroseriesdifference__derived_series__idx ON distroseriesdifference(derived_series);
CREATE INDEX distroseriesdifference__spph__idx ON distroseriesdifference(source_package_publishing_history);
CREATE INDEX distroseriesdifference__ignored__idx ON distroseriesdifference(ignored);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
