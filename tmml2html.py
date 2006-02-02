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

    def childelement(self, index, tag=None):
        node = self.content[index]
        if not isinstance(node, Element):
            return False
        elif tag is None:
            return True
        elif node.tag != tag:
            return False
        else:
            return True

    def indexrange(self):
        return xrange(len(self.content))

    def find(self, tag):
        for index in range(len(self.content)):
            if self.childelement(index):
                return self.content[index]
        else:
            raise IndexError


def parse(input):
    handler = ContentHandler()
    xml.sax.parse(input, handler)
    return handler.root[0]


class Node(object):

    labels = None

    def __init__(self, element):
        assert not isinstance(labels, basestring)
        if element.tag not in labels:
            raise ValueError
        self.element = element
        self._parse_children()

    def _parse_children(self):
        raise NotImplementedError


class Document(object):

    labels = ['TeXmacs']

    def _parse_children(self):
        body = self.element.find('body')
        for index in body.indexrange():
            if not node.childelement(index):
                continue
            assert node.tag == u'tm-par'
            self._append_paragraph(node.content)

    def _trim_whitespace(self, content):
        content = list(content)
        if content[0].isspace():
            del content[0]
        if content[-1].isspace():
            del content[-1]
        return content

    def _append_paragraph(self, content):
        # leading and trailing whitespace of paragraph are noise
        content = self._trim_whitespace(content)        
        if len(content) == 0:
            continue
        if len(content) == 1 and content[0].iselement():
            element = content[0]
            if element.tag == 'doc-data':
                if not (len(element.content) == 1 and element[0].iselement
            
            mixed = mixed_data(content[0])

def mixed_data(node):
    
                

t = parse('bzr-launchpad.tmml')
