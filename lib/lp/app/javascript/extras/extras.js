/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Things that YUI3 really needs.
 *
 * @module lp
 * @submodule extras
 */

YUI.add('lp.extras', function(Y) {

Y.log('loading lp.extras');

var namespace = Y.namespace("lp.extras"),
    NodeList = Y.NodeList;

/**
 * NodeList is crying out for map.
 * @static
 *
 * @param {Y.NodeList|Array} instance The node list or array of nodes
 *     (Node or DOM nodes) to map over.
 * @param {Function} fn The function to apply. It receives 1 argument:
 *     the current Node instance.
 * @param {Object} context optional An optional context to apply the
 *     function with. The default context is the current Node
 *     instance.
 */
NodeList.map = function(instance, fn, context) {
    return NodeList.getDOMNodes(instance).map(Y.one).map(
        function(node) {
            return fn.call(context || node, node);
        }
    );
};

/**
 * NodeList is crying out for map.
 *
 * @param {Function} fn The function to apply. It receives 1 argument:
 *     the current Node instance.
 * @param {Object} context optional An optional context to apply the
 *     function with. The default context is the current Node
 *     instance.
 */
NodeList.prototype.map = function(fn, context) {
    return NodeList.map(this, fn, context);
};

namespace.attrgetter = function(name) {
    return function(thing) {
        return thing[name];
    };
};

namespace.attrselect = function(name) {
    return function(things) {
        return Y.Array(things).map(attrgetter(name));
    };
};


}, "0.1", {requires: ["array-extras", "node"]});
