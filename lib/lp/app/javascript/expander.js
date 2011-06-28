/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Expander widget.  Can be used to let the user toggle the visibility of
 * existing elements on the page, or to make the page load elements on demand
 * as the user expands them.
 *
 * Each expander needs two tags as "connection points":
 *  * Icon tag, to be marked up with the expander icon.  Must have CSS class
 *    "expander-icon."
 *  * Content tag, to be exposed by the expander.  Must have CSS class
 *    "expander-content."
 *
 * The initial HTML may make either of these connection points invisible
 * initially by giving it the CSS class "unseen."  Setting up an expander then
 * makes its icon tag visible.  Opening an expander will make the content tag
 * visible, and closing an expander makes the content tag invisible.
 *
 * If you want the expander to load its data at runtime, you can provide a
 * loader function.  In that case, expanding an expander for the first time
 * sets a spinner and runs the loader.  The loader produces a DOM node and
 * feeds it to a callback function, which will enter the HTML into the content
 * tag.
 *
 * @module lp.app.widgets.expander
 * @requires node, event
 */

YUI.add('lp.app.widgets.expander', function(Y) {

var namespace = Y.namespace('lp.app.widgets.expander');

var connection_points = {
    icon_tag: '.expander-icon',
    content_tag: '.expander-content'
};

var state_markers = {
    expanded: 'expanded',
    loaded: 'expander-content-loaded',
    unseen: 'unseen'
};

var sprites = {
    expanded: 'treeExpanded',
    collapsed: 'treeCollapsed'
};

function getIconNode(node) {
    return node.one(connection_points.icon_tag);
}

function getContentNode(node) {
    return node.one(connection_points.content_tag);
}

namespace.getContentNode = getContentNode;

function isExpanded(node) {
    return node.hasClass(state_markers.expanded);
}

function setExpanded(node, is_expanded) {
    if (is_expanded) {
        node.addClass(state_markers.expanded);
    } else {
        node.removeClass(state_markers.expanded);
    }
}

function isLoaded(content_node) {
    return content_node.hasClass(state_markers.loaded);
}

function setLoaded(content_node) {
    content_node.addClass(state_markers.loaded);
}

function hideContentNode(content_node) {
    content_node.addClass(state_markers.unseen);
}

function showContentNode(content_node) {
    content_node.removeClass(state_markers.unseen);
}

function collapseIcon(icon_node) {
    icon_node.removeClass(sprites.expanded);
    icon_node.addClass(sprites.collapsed);
}

function expandIcon(icon_node) {
    icon_node.removeClass(sprites.collapsed);
    icon_node.addClass(sprites.expanded);
}

function updateContent(content_node, output_node) {
    setLoaded(content_node)
    content_node.get('children').remove(true);
    content_node.appendChild(output_node);
}

/*
 * Toggle the visibility of the expander targeted and the visual of
 * the expander itself.
 */
function toggleExpandableRow(node, loader) {
    var icon_node = getIconNode(node);
    var content_node = getContentNode(node);

    var is_expanded = isExpanded(content_node);
    if (is_expanded) {
        hideContentNode(content_node);
	collapseIcon(icon_node);
    } else {
        if (Y.Lang.isValue(loader) && !isLoaded(content_node)) {
            content_node.set('innerHTML', '<img src="/@@/spinner" />');
            function updater(output_node) {
                updateContent(content_node, output_node);
            }
            loader(node, updater);
        }
        expandIcon(icon_node);
        showContentNode(content_node);
    }
    setExpanded(content_node, !is_expanded);
}


/*
 * Turn an icon "connection point" into an expander.
 */
function enhanceExpanderIcon(icon_node) {
    icon_node.addClass('sprite').addClass('treeCollapsed');
    icon_node.removeClass(state_markers.unseen);
}


/*
 * Initialize expanders for tag(s) indicated by css_selector.
 *
 * @param css_selector CSS selector to specify exactly those tags that should
 *     be set up with expanders.
 * @param loader Optional function that loads or produces content on the fly.
 *     The function must accept two arguments: the Node for the expandable
 *     (so it matched css_selector), and a function that receives a DOM node
 *     that will replace the contents of the content node.
 */
function setupExpanders(css_selector, loader) {
    var expandables = Y.all(css_selector);

    var setuper = function(node) {
        var icon_node = getIconNode(node);
        hideContentNode(getContentNode(node));
        enhanceExpanderIcon(icon_node);
        icon_node.on('click', function(e) {
            e.preventDefault();
            toggleExpandableRow(
                e.currentTarget.ancestor(css_selector), loader);
        });
    };
    expandables.each(setuper);
}
namespace.setupExpanders = setupExpanders;

}, "0.1", {"requires": ["node"]});
