dot = '''
digraph g {
graph [
rankdir = "LR",
concentrate = true,
ratio = auto
];
node [
fontsize = "10",
shape = record
];
edge [
];

"emailaddress" [shape = record, label = "<col0> \N |  id:  serial\l email:  text\l person:  integer\l status:  integer\l" ];

"gpgkey" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l keyid:  text\l fingerprint:  text\l pubkey:  text\l revoked:  boolean\l algorithm:  integer\l keysize:  integer\l" ];

"ircid" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l network:  text\l nickname:  text\l" ];

"jabberid" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l jabberid:  text\l" ];

"karma" [shape = record, label = "<col0> \N |  id:  serial\l karmafield:  integer\l datecreated:  timestamp without time zone\l person:  integer\l points:  integer\l" ];

"logintoken" [shape = record, label = "<col0> \N |  id:  serial\l requester:  integer\l requesteremail:  text\l email:  text\l created:  timestamp without time zone\l tokentype:  integer\l token:  text\l" ];

"person" [shape = record, label = "<col0> \N |  id:  serial\l displayname:  text\l givenname:  text\l familyname:  text\l password:  text\l teamowner:  integer\l teamdescription:  text\l karma:  integer\l karmatimestamp:  timestamp without time zone\l name:  text\l language:  integer\l fti:  tsvector\l" ];

"personlabel" [shape = record, label = "<col0> \N |  person:  integer\l label:  integer\l" ];

"personlanguage" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l language:  integer\l" ];

"sshkey" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l keytype:  integer\l keytext:  text\l comment:  text\l" ];

"teammembership" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l team:  integer\l role:  integer\l status:  integer\l" ];

"teamparticipation" [shape = record, label = "<col0> \N |  id:  serial\l team:  integer\l person:  integer\l" ];

"wikiname" [shape = record, label = "<col0> \N |  id:  serial\l person:  integer\l wiki:  text\l wikiname:  text\l" ];


"emailaddress" -> "person" [label=""];
"gpgkey" -> "person" [label=""];
"ircid" -> "person" [label=""];
"jabberid" -> "person" [label=""];
"karma" -> "person" [label="karma_person_fk"];
"logintoken" -> "person" [label="logintoken_requester_fk"];
"person" -> "person" [label=""];
"personlabel" -> "person" [label=""];
"personlanguage" -> "person" [label="personlanguage_person_fk"];
"sshkey" -> "person" [label=""];
"teammembership" -> "person" [label=""];
"teammembership" -> "person" [label=""];
"teamparticipation" -> "person" [label=""];
"teamparticipation" -> "person" [label=""];
"wikiname" -> "person" [label=""];
}
'''

# Shorten timestamp declarations
import re
dot = re.subn('timestamp without time zone','timestamp', dot)[0]

lines = dot.split('\n')
for i in xrange(0, len(lines)):
    line = lines[i]
    if r'label = "<col0> \N' in line:
        m = re.search(r'''
                ^"(.*?)" .* 
                label \s = \s "<col0> \s \\N \s \| \s+ (.+?)" \s ];$
                ''', line, re.X)
        assert m is not None, 'Bad line %s' % repr(m)
        table = m.group(1)
        raw_cols = m.group(2)
        assert raw_cols.endswith(r'\l'), 'Bad column list'
        raw_cols = [
            r.strip() for r in raw_cols.split(r'\l') if r.strip()
            ]
        cols = [c.split(':') for c in raw_cols]
        cols = [(a.strip(), b.strip()) for a,b in cols]

        # This version looks nicer, but we have two cells for a table
        # column instead of one and we will have more difficulty using
        #label = r"{<col0>\N|{{"
        #for col, typ in cols:
        #    label += r"%s |" % col
        #label = label[:-1] + "}|{"
        #for col, typ in cols:
        #    label += r"%s |" % typ
        #label = label[:-1] + "}}}"
        #label = '"%s"' % label
        #shape = 'record'

        # This version is feature full, but looks crappy since we
        # can't control fonts or cell formatting
        #label = r"{<col0>\N | "
        #for col,typ in cols:
        #    label += r'<%s> %s: %s |' % (col, col, typ)
        #if label[-1] == '|':
        #    label = label[:-1]
        #label += "}"
        #label = '"%s"' % label
        #shape = 'record'

        # This version uses new HTML tables
        shape = 'plaintext'
        label = '''<
            <TABLE BGCOLOR="azure3" BORDER="1" ALIGN="LEFT" PORT="col1">
                <TR BORDER="1">
                    <TD BGCOLOR="white" COLSPAN="2" ALIGN="CENTER">\\N</TD>
                </TR>\n'''
        for col, typ in cols:
            label += '<TR BORDER="0" PORT="%s">\n' % col
            label += '<TD ALIGN="LEFT" BORDER="0">%s</TD>\n' % col
            label += '<TD ALIGN="LEFT" BORDER="0">%s</TD>\n' % typ
            label += '</TR>\n'
        label += '</TABLE>\n>'

        lines[i] = '"%s" [shape = %s, label = %s ];' % (table, shape, label)
    print lines[i]

