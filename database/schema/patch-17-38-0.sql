
SET client_min_messages TO error;

CREATE TABLE Calendar (
    id serial NOT NULL PRIMARY KEY,
    title text NOT NULL,
    revision integer NOT NULL
);

CREATE TABLE CalendarSubscription (
    id serial NOT NULL PRIMARY KEY,
    subject integer NOT NULL
        CONSTRAINT calendarsubscription_subject_fk REFERENCES Calendar,
    object integer NOT NULL
        CONSTRAINT calendarsubscription_object_fk REFERENCES Calendar,
    colour text NOT NULL DEFAULT '#9db8d2',
    CONSTRAINT calendarsubscription_subject_key UNIQUE (subject, object)
);

CREATE TABLE CalendarEvent (
    id serial NOT NULL PRIMARY KEY,
    uid varchar(255) NOT NULL CONSTRAINT calendarevent_uid_key UNIQUE,
    calendar integer NOT NULL
        CONSTRAINT calendarevent_calendar_fk REFERENCES Calendar,
    startdate timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    description text,
    location text
/*
    recurrence varchar(10) NOT NULL,
    count integer, / * if count is not positive, use until * /
    until timestamp without time zone,
    exceptions text,
    interval integer,
    rec_list text
*/
);


/* Add calendar column to Person table */

ALTER TABLE Person ADD COLUMN calendar integer;
ALTER TABLE Person ADD CONSTRAINT person_calendar_fk
    FOREIGN KEY (calendar) REFERENCES Calendar(id);
ALTER TABLE Person ADD CONSTRAINT person_calendar_key UNIQUE (calendar);

/* a field to store the user's selected timezone */
ALTER TABLE Person ADD COLUMN timezone text;

/* Add calendar column to Projects table */

ALTER TABLE Project ADD COLUMN calendar integer;
ALTER TABLE Project ADD CONSTRAINT project_calendar_fk
    FOREIGN KEY (calendar) REFERENCES Calendar(id);
ALTER TABLE Project ADD CONSTRAINT project_calendar_key UNIQUE (calendar);

/* Add calendar column to Products table */

ALTER TABLE Product ADD COLUMN calendar integer;
ALTER TABLE Product ADD CONSTRAINT product_calendar_fk
    FOREIGN KEY (calendar) REFERENCES Calendar(id);
ALTER TABLE Product ADD CONSTRAINT product_calendar_key UNIQUE (calendar);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 38, 0);

