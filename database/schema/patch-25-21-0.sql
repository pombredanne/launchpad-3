SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN addressline1 text;
ALTER TABLE Person ADD COLUMN addressline2 text;
ALTER TABLE Person ADD COLUMN organization text;
ALTER TABLE Person ADD COLUMN city text;
ALTER TABLE Person ADD COLUMN province text;
ALTER TABLE Person ADD COLUMN country integer REFERENCES Country (id);
ALTER TABLE Person ADD COLUMN postcode text;
ALTER TABLE Person ADD COLUMN phone text;

CREATE TABLE ShippingRun (
    id              serial NOT NULL PRIMARY KEY,
    datecreated     timestamp without time zone NOT NULL
);

CREATE TABLE Shipment (
    id              serial NOT NULL PRIMARY KEY,
    logintoken      text UNIQUE, -- Used to allow people which received CDs as
                                 -- part of an shock and awe campain to login
    shippingrun     integer NOT NULL,
    dateshipped     timestamp without time zone NOT NULL,
    shippingservice integer NOT NULL,
    trackingcode    text,
    priority        boolean
);

CREATE TABLE ShockAndAwe (
    id          serial NOT NULL PRIMARY KEY,
    name        text NOT NULL,
    title       text NOT NULL,
    description text NOT NULL
);

CREATE TABLE ShippingRequest (
    id          serial NOT NULL PRIMARY KEY,
    recipient   integer NOT NULL
                    CONSTRAINT shippingrequest_recipient_fk REFERENCES Person
                    CONSTRAINT is_person CHECK (is_person(recipient)),
    shipment    integer
                    CONSTRAINT shippingrequest_shipment_fk REFERENCES Shipment,
    whoapproved integer
                    CONSTRAINT shippingrequest_whoapproved_fk REFERENCES Person,
    -- Automatically approved or someone approved? NULL is auto-approved
    cancelled   boolean NOT NULL DEFAULT FALSE,
    -- The user can decide to cancel his request, or Marilize can do it.
    whocancelled integer
                    CONSTRAINT shippingrequest_whocancelled_fk REFERENCES Person,
    daterequested       timestamp without time zone NOT NULL,
    approved        boolean,

    shockandawe     integer,
    reason          text  -- People who requests things other than the
                          -- common options have to explain why they need
                          -- that. This will also let people explain 'why'
                          -- their large request should be approved.
);

-- For now, the distroarchrelease will be a dbschema value. That means that
-- we'll need to have things like EdUbuntu5.04-i386. If we use a combination
-- of flavour (EdUbuntu), release (5.04) and arch (i386) it'll be a lot easier
-- when adding new releases -- all we'll have to do is add a new entry in the
-- Release class.
CREATE TABLE RequestedCDs (
    id          serial NOT NULL PRIMARY KEY,
    request     integer NOT NULL
                    CONSTRAINT requestedcds_request_fk REFERENCES ShippingRequest,
    quantity    integer NOT NULL
                    CONSTRAINT quantity_is_positive CHECK ((quantity >= 0)),
    flavour     integer NOT NULL,
    distrorelease integer NOT NULL,
    architecture  integer NOT NULL,
    quantityapproved    integer
                    CONSTRAINT quantityapproved_is_positive 
                        CHECK ((quantityapproved >= 0))
);

CREATE TABLE StandardShipItRequest (
    id            serial NOT NULL PRIMARY KEY,
    quantityx86   integer NOT NULL
                    CONSTRAINT quantityx86_is_positive CHECK ((quantityx86 >= 0)),
    quantityppc   integer NOT NULL
                    CONSTRAINT quantityppc_is_positive CHECK ((quantityppc >= 0)),
    quantityamd64 integer NOT NULL
                    CONSTRAINT quantityamd64_is_positive CHECK ((quantityamd64 >= 0)),
    description   text NOT NULL,
    isdefault     boolean NOT NULL DEFAULT false,
    UNIQUE (quantityx86, quantityppc, quantityamd64)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,21,0);

