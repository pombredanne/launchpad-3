
SET client_min_messages TO error;

CREATE TABLE Calendar (
    id serial NOT NULL PRIMARY KEY,
    owner integer NOT NULL,
    title text NOT NULL,
    revision integer NOT NULL
);

CREATE TABLE CalendarSubscription (
    id serial NOT NULL PRIMARY KEY,
    person integer NOT NULL,
    calendar integer NOT NULL,
    colour text NOT NULL DEFAULT '#9db8d2',

    CONSTRAINT calendarsubscription_sub_key UNIQUE (person, calendar)
);

CREATE TABLE CalendarEvent (
    id serial NOT NULL PRIMARY KEY,
    unique_id varchar(255) NOT NULL,
    calendar integer NOT NULL,
    dtstart timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    location text NOT NULL DEFAULT '',
    recurrence varchar(10) NOT NULL,
    count integer, /* if count is not positive, use until */
    until timestamp without time zone,
    exceptions text,
    interval integer,
    rec_list text,

    CONSTRAINT calendarevent_unique_id_key UNIQUE (unique_id)
);

ALTER TABLE Calendar
    ADD CONSTRAINT "calendar_owner_fk" FOREIGN KEY (owner) REFERENCES Person(id);

ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "calendarsubscription_person_fk" FOREIGN KEY (person) REFERENCES Person(id);
ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "calendarsubscription_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);

ALTER TABLE CalendarEvent
    ADD CONSTRAINT "calendarevent_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);



/* Add calendar column to Person table */

ALTER TABLE Person ADD COLUMN calendar integer;
ALTER TABLE Person
    ADD CONSTRAINT "person_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);
ALTER TABLE Person ADD COLUMN timezone_name text;

/* Add calendar column to Projects table */

ALTER TABLE Project ADD COLUMN calendar integer;
ALTER TABLE Project
    ADD CONSTRAINT "project_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);

/* Add calendar column to Products table */

ALTER TABLE Product ADD COLUMN calendar integer;
ALTER TABLE Product
    ADD CONSTRAINT "product_calendar_fk" FOREIGN KEY (calendar) REFERENCES Calendar(id);

/* security stuff -- should move to security.cfg */
GRANT SELECT, INSERT, UPDATE ON Calendar TO GROUP write;
GRANT SELECT, INSERT, UPDATE, DELETE ON CalendarSubscription TO GROUP write;
GRANT SELECT, INSERT, UPDATE, DELETE ON CalendarEvent TO GROUP write;

GRANT SELECT, INSERT, UPDATE ON calendar_id_seq TO GROUP write;
GRANT SELECT, INSERT, UPDATE ON calendarsubscription_id_seq TO GROUP write;
GRANT SELECT, INSERT, UPDATE ON calendarevent_id_seq TO GROUP write;
