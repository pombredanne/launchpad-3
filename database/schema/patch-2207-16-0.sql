SET client_min_messages=ERROR;

CREATE TABLE lp_TeamParticipation AS SELECT * FROM TeamParticipation;
ALTER TABLE lp_TeamParticipation
    ADD CONSTRAINT lp_TeamParticipation_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_TeamPerticipation__team__person__key
        UNIQUE (team, person);
CREATE INDEX lp_TeamParticipation__person__idx ON lp_TeamParticipation(person);


CREATE TABLE lp_PersonLocation AS SELECT * FROM PersonLocation;
ALTER TABLE lp_PersonLocation
    ADD CONSTRAINT lp_PersonLocation_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_PersonLocation__person__key UNIQUE (person);


CREATE TABLE lp_Person AS SELECT * FROM Person;
ALTER TABLE lp_Person
    ADD CONSTRAINT lp_Person_pkey PRIMARY KEY (id),
    ADD CONSTRAINT lp_Person__name__key UNIQUE (name),
    ADD CONSTRAINT lp_Person__account__key UNIQUE (account);


-- Insert triggers
CREATE OR REPLACE FUNCTION lp_mirror_teamparticipation_ins() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    INSERT INTO lp_TeamParticipation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_teamparticipation_ins_t
AFTER INSERT ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_teamparticipation_ins();

CREATE OR REPLACE FUNCTION lp_mirror_personlocation_ins() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    INSERT INTO lp_PersonLocation SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_personlocation_ins_t
AFTER INSERT ON PersonLocation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_personlocation_ins();

CREATE OR REPLACE FUNCTION lp_mirror_person_ins() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    INSERT INTO lp_Person SELECT NEW.*;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_person_ins_t
AFTER INSERT ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_person_ins();


-- UPDATE triggers
CREATE  OR REPLACE FUNCTION lp_mirror_teamparticipation_upd() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    UPDATE lp_TeamParticipation
    SET id = NEW.id,
        team = NEW.team,
        person = NEW.person
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_teamparticipation_upd_t
AFTER UPDATE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_teamparticipation_upd();

CREATE  OR REPLACE FUNCTION lp_mirror_personlocation_upd() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    UPDATE lp_PersonLocation
    SET id = NEW.id,
        date_created = NEW.date_created,
        person = NEW.person,
        latitude = NEW.latitude,
        longitude = NEW.longitude,
        time_zone = NEW.time_zone,
        last_modified_by = NEW.last_modified_by,
        date_last_modified = NEW.date_last_modified,
        visible = NEW.visible,
        locked = NEW.locked
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_personlocation_upd_t
AFTER UPDATE ON PersonLocation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_personlocation_upd();

CREATE  OR REPLACE FUNCTION lp_mirror_person_upd() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    UPDATE lp_Person
    SET id = NEW.id,
        displayname = NEW.displayname,
        teamowner = NEW.teamowner,
        teamdescription = NEW.teamdescription,
        name = NEW.name,
        language = NEW.language,
        fti = NEW.fti,
        defaultmembershipperiod = NEW.defaultmembershipperiod,
        defaultrenewalperiod = NEW.defaultrenewalperiod,
        subscriptionpolicy = NEW.subscriptionpolicy,
        merged = NEW.merged,
        datecreated = NEW.datecreated,
        addressline1 = NEW.addressline1,
        addressline2 = NEW.addressline2,
        organization = NEW.organization,
        city = NEW.city,
        province = NEW.province,
        country = NEW.country,
        postcode = NEW.postcode,
        phone = NEW.phone,
        homepage_content = NEW.homepage_content,
        icon = NEW.icon,
        mugshot = NEW.mugshot,
        hide_email_addresses = NEW.hide_email_addresses,
        creation_rationale = NEW.creation_rationale,
        creation_comment = NEW.creation_comment,
        registrant = NEW.registrant,
        logo = NEW.logo,
        renewal_policy = NEW.renewal_policy,
        personal_standing = NEW.personal_standing,
        personal_standing_reason = NEW.personal_standing_reason,
        mail_resumption_date = NEW.mail_resumption_date,
        mailing_list_auto_subscribe_policy 
            = NEW.mailing_list_auto_subscribe_policy,
        mailing_list_receive_duplicates = NEW.mailing_list_receive_duplicates,
        visibility = NEW.visibility,
        verbose_bugnotifications = NEW.verbose_bugnotifications,
        account = NEW.account
    WHERE id = OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_person_upd_t
AFTER UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_person_upd();

-- Delete triggers
CREATE OR REPLACE FUNCTION lp_mirror_del() RETURNS trigger
LANGUAGE plpgsql AS
$$
BEGIN
    EXECUTE 'DELETE FROM lp_' || TG_TABLE_NAME || ' WHERE id=' || OLD.id;
    RETURN NULL; -- Ignored for AFTER triggers.
END;
$$;

CREATE TRIGGER lp_mirror_teamparticipation_del_t
AFTER DELETE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_personlocation_del_t
AFTER DELETE ON TeamParticipation
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();

CREATE TRIGGER lp_mirror_person_del_t
AFTER DELETE ON Person
FOR EACH ROW EXECUTE PROCEDURE lp_mirror_del();


INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 16, 0);

