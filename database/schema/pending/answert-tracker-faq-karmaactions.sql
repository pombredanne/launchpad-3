INSERT INTO karmaaction (category, points, name, title, summary)
VALUES ((SELECT id FROM KarmaCategory WHERE name = 'answers'),
        5, 'faqcreated', 'FAQ created',
        'User create a new FAQ in Launchpad.');

INSERT INTO karmaaction (category, points, name, title, summary)
VALUES ((SELECT id FROM KarmaCategory WHERE name = 'answers'),
        1, 'faqedited', 'FAQ edited',
        'User updated the details of a FAQ in Launchpad.');
