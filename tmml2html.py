import xml.sax
import xml.sax.handler


class ContentHandler(xml.sax.handler.ContentHandler):

    def startDocument(self):
        self.root = []
        self.parents = []
        self.current = None

    def endDocument(self):
        pass

    def startElement(self, tag, attrs):
        if self.current is not None:
            self.parents.append(self.current)
        attrs_dict = dict((name, attrs.getValue(name))
                           for name in attrs.getNames())
        self.current = Element(tag, attrs_dict)

    def endElement(self, name):
        if not self.parents:
            self.root.append(self.current)
            self.current = None
        else:
            parent = self.parents.pop(-1)
            parent.append_element(self.current)
            self.current = parent

    def characters(self, content):
        self.current.append_text(content)

    def ignorableWhitespace(self, whitespace):
        self.current.append_text(content)


class Element(object):

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.content = []

    def append_element(self, element):
        self.content.append(element)

    def append_text(self, text):
        if self.content and isinstance(self.content[-1], basestring):
            self.content[-1] += text
        else:
            self.content.append(text)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self.attrs[key]
        elif isinstance(key, int):
            return self.content[key]
        else:
            raise KeyError

    def __repr__(self):
        return '<Element %r>' % (self.tag,)

def parse(input):
    handler = ContentHandler()
    xml.sax.parse(input, handler)
    return handler.root[0]


class Node(object):

    labels = None
    children = None

    def __init__(self, element):
        assert not isinstance(labels, basestring)
        if element.tag not in labels:
            raise ValueError
        self.element = element
        self._parse_children()

    def _parse_children(self):
        for child in self.element.getchildren():
            if child.tag not in self.children:
                raise ValueError


class Texmacs(object):

    labels = ['TeXmacs']

    def __init__(self, element):
        pass

t = parse('bzr-launchpad.tmml')
