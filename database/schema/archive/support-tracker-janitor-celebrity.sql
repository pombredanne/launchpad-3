-- Create the support-tracker-janitor celebrity

INSERT INTO person (displayname, "password", teamowner, teamdescription, name, "language", defaultmembershipperiod, defaultrenewalperiod, subscriptionpolicy, merged, calendar, timezone, addressline1, addressline2, organization, city, province, country, postcode, phone, homepage_content, emblem, hackergotchi, hide_email_addresses,
creation_rationale)
VALUES ('Support Tracker Janitor', NULL, NULL, NULL, 'support-tracker-janitor',
        NULL, NULL, NULL, 1, NULL, NULL, 'UTC', NULL, NULL, NULL, NULL, NULL, NULL,
        NULL, NULL, NULL, NULL, NULL, true, 1);

INSERT INTO emailaddress (email, person, status)
VALUES ('janitor@support.launchpad.net',
        (SELECT id FROM person WHERE name = 'support-tracker-janitor'), 4);

INSERT INTO wikiname (person, wiki, wikiname)
VALUES ((SELECT id FROM person WHERE name = 'support-tracker-janitor'),
         'https://wiki.ubuntu.com/', 'SupportTrackerJanitor');
