
SET client_min_messages TO error;

CREATE TABLE Calendar (
    id serial NOT NULL PRIMARY KEY,
    title text NOT NULL,
    revision integer NOT NULL
);

CREATE TABLE CalendarSubscription (
    id serial NOT NULL PRIMARY KEY,
    subject integer NOT NULL,
    object integer NOT NULL,
    colour text NOT NULL DEFAULT '#9db8d2',

    CONSTRAINT calendarsubscription_sub_key UNIQUE (subject, object)
);

CREATE TABLE CalendarEvent (
    id serial NOT NULL PRIMARY KEY,
    unique_id varchar(255) NOT NULL,
    calendar integer NOT NULL,
    dtstart timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    location text DEFAULT '',
/*
    recurrence varchar(10) NOT NULL,
    count integer, / * if count is not positive, use until * /
    until timestamp without time zone,
    exceptions text,
    interval integer,
    rec_list text,
*/

    CONSTRAINT calendarevent_unique_id_key UNIQUE (unique_id)
);

ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "calendarsubscription_subject_fk" FOREIGN KEY (subject) REFERENCES Calendar(id);
ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "calendarsubscription_object_fk" FOREIGN KEY (object) REFERENCES Calendar(id);

ALTER TABLE CalendarEvent
    ADD CONSTRAINT "calendarevent_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);



/* Add calendar column to Person table */

ALTER TABLE Person ADD COLUMN calendar integer;
ALTER TABLE Person
    ADD CONSTRAINT "person_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);
CREATE INDEX person_calendar_idx ON Person (calendar);

/* a field to store the user's selected timezone */
ALTER TABLE Person ADD COLUMN timezone_name text;

/* Add calendar column to Projects table */

ALTER TABLE Project ADD COLUMN calendar integer;
ALTER TABLE Project
    ADD CONSTRAINT "project_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);
CREATE INDEX project_calendar_idx ON Project (calendar);

/* Add calendar column to Products table */

ALTER TABLE Product ADD COLUMN calendar integer;
ALTER TABLE Product
    ADD CONSTRAINT "product_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);
CREATE INDEX product_calendar_idx ON Product (calendar);
