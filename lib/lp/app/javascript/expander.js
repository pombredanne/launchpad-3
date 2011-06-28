/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Expander widget.  Can be used to let the user toggle the visibility of
 * existing elements on the page, or to make the page load elements on demand
 * as the user expands them.
 *
 * Synonyms: collapsible, foldable.
 *
 * Each expander needs two tags as "connection points":
 *  * Icon tag, to be marked up with the expander icon.  Must have CSS class
 *    "expander-icon."
 *  * Content tag, to be exposed by the expander.  Must have CSS class
 *    "expander-content."
 *
 * Either may have initial contents.  The initial contents of the icon tag
 * will be retained, so it could say something like "Details..." that explains
 * what the icon means.  You'll want to hide it using the "unseen" class if
 * these contents should only be shown once the expander has been set up.
 *
 * Any initial contents of the content tag will be revealed when the expander
 * is opened; hide them using the "unseen" class if they should not be shown
 * when the expander has not been enabled.  An optional loader function may
 * produce new contents for this tag when it is first opened.
 *
 * If you provide a loader function, the expander inserts a spinner before any
 * other elements in the content tag and runs the loader.  The loader produces
 * a DOM node and feeds it to a callback function, which will enter the HTML
 * into the content tag.
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

/*
 * Is the content node currently expanded?
 */
function isExpanded(content_node) {
    return content_node.hasClass(state_markers.expanded);
}

/*
 * Record the expanded/collapsed state of the content tag.
 */
function setExpanded(content_node, is_expanded) {
    if (is_expanded) {
        content_node.addClass(state_markers.expanded);
    } else {
        content_node.removeClass(state_markers.expanded);
    }
}

/*
 * Has the content loader for the expander been started?
 */
function isLoaded(content_node) {
    return content_node.hasClass(state_markers.loaded);
}

/*
 * Record that the content loader has been started.
 */
function setLoaded(content_node) {
    content_node.addClass(state_markers.loaded);
}

/*
 * Hide the content node (by adding the "unseen" class to it).
 */
function hideContentNode(content_node) {
    content_node.addClass(state_markers.unseen);
}

/*
 * Reveal the content node (by removing the "unseen" class from it).
 */
function showContentNode(content_node) {
    content_node.removeClass(state_markers.unseen);
}

/*
 * Set icon to the "collapsed" state.
 */
function collapseIcon(icon_node) {
    icon_node.removeClass(sprites.expanded);
    icon_node.addClass(sprites.collapsed);
}

/*
 * Set icon to the "expanded" state.
 */
function expandIcon(icon_node) {
    icon_node.removeClass(sprites.collapsed);
    icon_node.addClass(sprites.expanded);
}

/*
 * Process the output node being produced by the loader.
 */
function receiveContent(content_node, output_node) {
    content_node.setContent(output_node);
}

/*
 * Insert a spinner at the beginning of the content tag.
 */
function addSpinner(content_node) {
    var spinner_node = Y.Node.create('<img/>');
    spinner_node.set('src', '/@@/spinner');
    content_node.prepend(spinner_node);
}

/*
 * Show spinner and invoke the expander's loader.
 */
function load(icon_node, content_node, loader) {
    addSpinner(content_node);
    setLoaded(content_node);
    function updater(output_node) {
        receiveContent(content_node, output_node);
    }
    loader(icon_node, content_node, updater);
}

/*
 * Toggle the visibility of the expander targeted and the visual of
 * the expander itself.
 */
function toggleExpander(icon_node, content_node, loader) {
    var is_expanded = isExpanded(content_node);

    if (is_expanded) {
        hideContentNode(content_node);
        collapseIcon(icon_node);
    } else {
        if (Y.Lang.isValue(loader) && !isLoaded(content_node)) {
            load(icon_node, content_node, loader);
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
 * Set up an expander.
 *
 * @param icon_node Node for the icon tag.
 * @param content_node Node for the content tag.
 * @param loader A function that produces the ultimate contents for the
 *     content tag.  Will receive as its arguments: icon_node, content_node,
 *     and a callback function.  It should construct a new node that will
 *     replace whatever is inside the content tag, and feed it to the
 *     callback.
 */
function createExpander(icon_node, content_node, loader) {
    hideContentNode(content_node);
    enhanceExpanderIcon(icon_node);
    icon_node.on('click', function(e) {
        e.preventDefault();
        toggleExpander(icon_node, content_node, loader);
    });
}
namespace.createExpander = createExpander;

/*
 * Initialize expanders based on CSS selectors.
 *
 * @param widget_select CSS selector to specify each tag that will have an
 *     expander created inside it.
 * @param icon_select CSS selector for the icon tag inside each tag matched
 *     by widget_select.
 * @param content_select CSS selector for the content tag inside each tag
 *     matched by widget_select.
 * @param loader Optional loader function to be passed to createExpander for
 *     each expander that is set up.
 */
function createByCSS(widget_select, icon_select, content_select, loader) {
    Y.all(widget_select).each(function(widget) {
        createExpander(
            widget.one(icon_select), widget.one(content_select), loader);
    });
}
namespace.createByCSS = createByCSS;

}, "0.1", {"requires": ["node"]});
