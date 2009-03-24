SET client_min_messages=ERROR;

CREATE TABLE HWDMIHandle (
    id serial PRIMARY KEY,
    handle integer NOT NULL,
    type integer NOT NULL,
    submission integer REFERENCES HWSubmission
);

CREATE INDEX hwdmihandle__submission__idx ON HWDMIHandle(submission);

CREATE TABLE HWDMIValue (
    id serial primary key,
    key text,
    value text,
    handle integer NOT NULL REFERENCES HWDMIHandle(id)
);

CREATE INDEX hwdmivalue__hanlde__idx ON HWDMIValue(handle);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 36, 0);
