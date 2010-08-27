SET client_min_messages=ERROR;

CREATE TABLE DistroSeriesDifference (
    id serial PRIMARY KEY,
    derived_series integer NOT NULL CONSTRAINT distroseriesdifference__derived_series__fk REFERENCES distroseries,
    source_package_name integer NOT NULL CONSTRAINT distroseriesdifference__source_package_name__fk REFERENCES sourcepackagename,
    last_package_diff integer CONSTRAINT distroseriesdifference__last_package_diff__fk REFERENCES packagediff,
    status integer NOT NULL,
    difference_type integer NOT NULL
);
CREATE INDEX distroseriesdifference__derived_series__idx ON distroseriesdifference(derived_series);
CREATE INDEX distroseriesdifference__source_package_name__idx ON distroseriesdifference(source_package_name);
CREATE INDEX distroseriesdifference__status__idx ON distroseriesdifference(status);
CREATE INDEX distroseriesdifference__difference_type__idx ON distroseriesdifference(difference_type);
CREATE INDEX distroseriesdifference__last_package_diff__idx ON distroseriesdifference(last_package_diff);

CREATE TABLE DistroSeriesDifferenceMessage(
    id serial PRIMARY KEY,
    distro_series_difference integer NOT NULL CONSTRAINT distroseriesdifferencemessage__distro_series_difference__fk REFERENCES distroseriesdifference,
    message integer NOT NULL CONSTRAINT distroseriesdifferencemessage__message__fk REFERENCES message,
    UNIQUE (distro_series_difference, message)
);
CREATE INDEX distroseriesdifferencemessage__distroseriesdifference__idx ON distroseriesdifferencemessage(distro_series_difference);
CREATE INDEX distroseriesdifferencemessage__message__idx ON distroseriesdifferencemessage(message);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 07, 0);
