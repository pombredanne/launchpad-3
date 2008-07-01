SET client_min_messages=ERROR;

CREATE TABLE ShipItSurvey (
    id serial PRIMARY KEY,
    person integer NOT NULL REFERENCES Person,
    date_created timestamp WITHOUT TIME ZONE
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    exported boolean NOT NULL DEFAULT FALSE
);

CREATE TABLE ShipItSurveyQuestion (
    id serial PRIMARY KEY,
    question TEXT NOT NULL UNIQUE
);

CREATE TABLE ShipItSurveyAnswer (
    id serial PRIMARY KEY,
    answer TEXT NOT NULL UNIQUE
);

CREATE TABLE ShipItSurveyResult (
    id serial PRIMARY KEY,
    survey integer NOT NULL REFERENCES ShipItSurvey,
    question integer NOT NULL REFERENCES ShipItSurveyQuestion,
    answer integer REFERENCES ShipItSurveyAnswer
);

-- For quick exports
CREATE UNIQUE INDEX shipitsurvey__unexported__key ON ShipItSurvey(id)
    WHERE exported IS FALSE;

-- For people merge
CREATE INDEX shipitsurvey__person__idx ON ShipItSurvey(person);

-- For reports
CREATE INDEX shipitsurveyresult__survey__question__answer__idx
    ON ShipItSurveyResult(survey, question, answer);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 29, 0);
