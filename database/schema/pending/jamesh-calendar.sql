
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
    calendar integer NOT NULL
);

CREATE TABLE CalendarEvent (
    id serial NOT NULL PRIMARY KEY,
    unique_id varchar(255) NOT NULL,
    calendar integer NOT NULL,
    dtstart timestamp without time zone NOT NULL,
    duration interval NOT NULL,
    title text NOT NULL,
    location text NOT NULL,
    recurrence varchar(10) NOT NULL,
    count integer, /* if count is not positive, use until */
    until timestamp without time zone,
    exceptions text,
    interval integer,
    rec_list text,

    CONSTRAINT unique_unique_id UNIQUE (unique_id)
);

ALTER TABLE Calendar
    ADD CONSTRAINT "$1" FOREIGN KEY (owner) REFERENCES Person(id);

ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "$1" FOREIGN KEY (person) REFERENCES Person(id);
ALTER TABLE CalendarSubscription
    ADD CONSTRAINT "$2" FOREIGN KEY (calendar) REFERENCES Calendar(id);

ALTER TABLE CalendarEvent
    ADD CONSTRAINT "$1" FOREIGN KEY (calendar) REFERENCES Calendar(id);



/* Add calendar column to Person table */

ALTER TABLE Person ADD COLUMN calendar integer;
ALTER TABLE Person
    ADD CONSTRAINT "$2" FOREIGN KEY (calendar) REFERENCES Calendar(id);
