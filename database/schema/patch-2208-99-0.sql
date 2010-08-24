SET client_min_messages=ERROR;

CREATE TABLE DistroSeriesDifference (
    id serial PRIMARY KEY,
    derived_series integer NOT NULL CONSTRAINT distroseriesdifference__derived_series__fk REFERENCES distroseries,
    source_package_name integer NOT NULL CONSTRAINT distroseriesdifference__source_package_name__fk REFERENCES sourcepackagename,
    activity_log text,
    status integer NOT NULL
);
CREATE INDEX distroseriesdifference__derived_series__idx ON distroseriesdifference(derived_series);
CREATE INDEX distroseriesdifference__source_package_name__idx ON distroseriesdifference(source_package_name);
CREATE INDEX distroseriesdifference__status__idx ON distroseriesdifference(status);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
