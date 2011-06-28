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
 * makes its icon tag visible, but collapses the content.  Clients that do
 * not run the script will of course continue the show or hide the content
 * depending on whether the HTML adds the "unseen" class.
 *
 * Opening an expander will make the content tag visible, and closing an
 * expander makes the content tag invisible again.
 *
 * If you want the expander to load its data at runtime, you can provide a
 * loader function.  In that case, expanding an expander for the first time
 * inserts a spinner before any other elements in the content tag and runs the
 * loader.  The loader produces a DOM node and feeds it to a callback
 * function, which will enter the HTML into the content tag.
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

function getIconNode(expander_node) {
    return expander_node.one(connection_points.icon_tag);
}

function getContentNode(expander_node) {
    return expander_node.one(connection_points.content_tag);
}

namespace.getContentNode = getContentNode;

function isExpanded(content_node) {
    return content_node.hasClass(state_markers.expanded);
}

function setExpanded(content_node, is_expanded) {
    if (is_expanded) {
        content_node.addClass(state_markers.expanded);
    } else {
        content_node.removeClass(state_markers.expanded);
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
    setLoaded(content_node);
    content_node.setContent(output_node);
}

function addSpinner(content_node) {
    var spinner_node = Y.Node.create('<img/>');
    spinner_node.set('src', '/@@/spinner');
    content_node.prepend(spinner_node);
}

function load(expander_node, content_node, loader) {
    addSpinner(content_node);
    function updater(output_node) {
        updateContent(content_node, output_node);
    }
    loader(expander_node, updater);
}

/*
 * Toggle the visibility of the expander targeted and the visual of
 * the expander itself.
 */
function toggleExpander(expander_node, loader) {
    var icon_node = getIconNode(expander_node);
    var content_node = getContentNode(expander_node);
    var is_expanded = isExpanded(content_node);

    if (is_expanded) {
        hideContentNode(content_node);
        collapseIcon(icon_node);
    } else {
        if (Y.Lang.isValue(loader) && !isLoaded(content_node)) {
            load(expander_node, content_node, loader);
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


function createExpander(expander_node, loader) {
    var icon_node = getIconNode(expander_node);
    hideContentNode(getContentNode(expander_node));
    enhanceExpanderIcon(icon_node);
    icon_node.on('click', function(e) {
        e.preventDefault();
        toggleExpander(expander_node, loader);
    });
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
    Y.all(css_selector).each(function(expander_node) {
        createExpander(expander_node, loader);
    });
}
namespace.setupExpanders = setupExpanders;

}, "0.1", {"requires": ["node"]});
