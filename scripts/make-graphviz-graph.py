#!/usr/bin/env python
"""Read xmlrpc data from stdin.  Write rendered graph data to stdout.

The xmlrpc method name is the format of graph to use.  See allowed_formats
for the names that are recognized.

The xmlrpc params is a two-tuple (nodes, connections).

nodes is a list of node dicts.
A node dict is a dict that has the following key/value pairs:

  name: str, unique name of this node.
  URL: str
  label: str
  comment: str
  color: str
  fontname: str
  fontsize: int

connections is a list of two-tuples (from_name, to_name).
These indicate node names that are directionally connected.

"""

import sys
import xmlrpclib
import yapgvb
from tempfile import TemporaryFile


allowed_formats = set(['png', 'cmapx'])


def main():
    """Read xmlrpc data from stdin.  Render the graph to stdout."""
    input = sys.stdin.read()
    data = xmlrpclib.loads(input)

    params, methodname = data
    format = methodname
    global allowed_formats
    if format not in allowed_formats:
        raise RuntimeError('bad format: %s' % format)

    nodes, connections = params
    graph = create_graph(nodes, connections)

    # Sadly, the yapgvb bindings don't allow use of a stringio here.
    # So we have to use a tempfile instead.
    tmpfile = TemporaryFile()
    graph.render(tmpfile, format=str(format))
    tmpfile.seek(0)
    output = tmpfile.read()

    sys.stdout.writelines(output)


def create_graph(nodes, connections):
    """Create and render a graphhviz graph of the nodes and connections.

    Return the rendered graph object.
    """
    graph = yapgvb.Graph('deptree')
    gv_nodes = {}
    for node in nodes:
        gv_node = graph.add_node(str(node['name']))
        gv_node.color = str(node['color'])
        gv_node.URL = str(node['URL'])
        gv_node.fontname = str(node['fontname'])
        gv_node.fontsize = node['fontsize']
        gv_node.comment = str(node['comment'])
        gv_node.label = str(node['label'])
        gv_nodes[node['name']] = gv_node

    for from_node, to_node in connections:
        gv_from_node = gv_nodes[from_node]
        gv_to_node = gv_nodes[to_node]
        gv_edge = gv_from_node >> gv_to_node
        gv_edge.arrowhead = 'normal'

    graph.mode = 'hier'
    graph.sep = 0.5
    graph.layout(yapgvb.engines.dot)
    return graph


if __name__ == '__main__':
    main()

