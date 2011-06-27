/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Expander widget.
 *
 * @module lp.app.widgets.expander
 * @requires node, lazr.choiceedit, lp.client.plugins
 */

YUI.add('lp.app.widgets.expander', function(Y) {

var namespace = Y.namespace('lp.app.widgets.expander');

function getToggleIcon(node) {
    return node.one('.expander-icon');
}

function getContentNode(node) {
    return node.one('.expander-content');
}
namespace.getContentNode = getContentNode;

function isExpanded(node) {
    return node.hasClass('expanded');
}

function setExpanded(node, is_expanded) {
    if (is_expanded) {
        node.addClass('expanded');
    } else {
        node.removeClass('expanded');
    }
}

function isLoaded(node) {
    return node.hasClass('loaded');
}

function setLoaded(node) {
    node.addClass('loaded');
}

function hideContentNode(node) {
    node.addClass('unseen');
}

function showContentNode(node) {
    node.removeClass('unseen');
}

/*
 * Toggle the visibility of the expander targeted and the visual of
 * the expander itself.
 */
function toggleExpandableRow(node, loader) {
    var toggle_icon = getToggleIcon(node);
    var content = getContentNode(node);

    var is_expanded = isExpanded(content);
    setExpanded(content, !is_expanded);
    if (is_expanded) {
        hideContentNode(content);
        toggle_icon.removeClass('treeExpanded');
        toggle_icon.addClass('treeCollapsed');
    } else {
        showContentNode(content);
        if (!isLoaded(content)) {
            loader(node);
        }
        toggle_icon.removeClass('treeCollapsed');
        toggle_icon.addClass('treeExpanded');
    }
}

function setupExpanders(css_selector, loader) {
    var expandables = Y.all(css_selector);

    var setuper = function(node) {
        var toggle_icon = getToggleIcon(node);
        var content_node = getContentNode(node);
        hideContentNode(content_node);
        toggle_icon
            .addClass('sprite')
            .addClass('treeCollapsed')
            .addClass('js-action');
        toggle_icon.on('click', function(e) {
            e.preventDefault();
            toggleExpandableRow(
                e.currentTarget.ancestor('.expandable'), loader);
        });
    };
    expandables.each(setuper);
}
namespace.setupExpanders = setupExpanders;

}, "0.1", {"requires": ["node"]});
