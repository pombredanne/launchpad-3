
COMMENT ON TABLE Bounty IS 'A set of bounties for work to be done by the open source community. These bounties will initially be offered only by Canonical, but later we will create the ability for people to offer the bounties themselves, using us as a clearing house.';
COMMENT ON COLUMN Bounty.usdvalue IS 'This is the ESTIMATED value in US Dollars of the bounty. We say "estimated" because the bounty might one day be offered in one of several currencies, or people might contribute different amounts in different currencies to each bounty. This field will reflect an estimate based on recent currency exchange rates of the value of this bounty in USD.';
COMMENT ON COLUMN Bounty.difficulty IS 'An estimate of the difficulty of the bounty, from 1 to 100, where 100 is extremely difficult and 1 is extremely easy.';
COMMENT ON COLUMN Bounty.duration IS 'An estimate of the length of time it should take to complete this bounty, given the skills required.';
COMMENT ON COLUMN Bounty.reviewer IS 'The person who will review this bounty regularly for progress. The reviewer is the person who is responsible for establishing when the bounty is complete.';
COMMENT ON COLUMN Bounty.owner IS 'The person who created the bounty. The owner can update the specification of the bounty, and appoints the reviewer.';

