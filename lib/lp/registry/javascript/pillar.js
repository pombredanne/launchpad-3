
/** Copyright (c) 2010, Canonical Ltd. All rights reserved.
 *
 * Pillar configuration ui hiding.
 *
 * @module lp.registry.pillar
 */

YUI.add('lp.registry.pillar', function(Y) {

var module = Y.namespace('lp.registry.pillar');

module.activate_collapsible_div = function() {
    // Grab the collapsibles.
    Y.all('div.collapsible').each(function(collapsible) {

    var legend = collapsible.one('span#legend');
    if (legend === null ||
        legend.one('.collapseIcon') !== null) {
            // If there's no legend there's not much we can do,
            // so just exit this iteration. If there's a
            // collapseIcon in there we consider the collapsible
            // to already have been set up and therefore ignore
            // it this time around.
            return;
        }

        var icon = Y.Node.create(
            '<img src="/@@/treeExpanded" class="collapseIcon" />');

        // We use javascript:void(0) here (though it will cause
        // lint to complain) because it prevents clicking on the
        // anchor from altering the page URL, which can subtly
        // break things.
        var anchor = Y.Node.create(
            '<a href="javascript:void(0);"></a>');
        anchor.appendChild(icon);

        // Move the contents of the legend into the span. We use
        // the verbose version of <span /> to avoid silly
        // breakages in Firefox.
        var span = Y.Node.create('<span></span>');
        var legend_children = legend.get('children');
        var len;

        if (Y.Lang.isValue(legend_children)) {
            // XXX 2009-07-06 gmb Account for oddness from
            // Node.get('children'); (see YUI ticket 2528028 for
            // details).
            len = legend_children.size ?
                legend_children.size() : legend_children.length;
        } else {
            len = 0;
        }

        if (len > 0) {
            // If the legend has child elements, move them
            // across one by one.
            Y.each(legend_children, function(child_node) {
                if (child_node.get('tagName') == 'A') {
                    // If this child is an anchor, add only its
                    // contents to the span.
                    new_node = Y.Node.create(
                        child_node.get('innerHTML'));
                    span.appendChild(new_node);
                    legend.removeChild(child_node);
                } else {
                    // Otherwise, add the node to the span as it
                    // is.
                    span.appendChild(child_node);
                }
            });
        } else {
            // Otherwise just move the innerHTML across as a
            // block. Once the span is appended to the anchor,
            // this will essentially turn the contents of the
            // legend into a link.
            span.set('innerHTML', legend.get('innerHTML'));
            legend.set('innerHTML', '');
        }

        // Replace the contents of the legend with the anchor.
        anchor.appendChild(span);
        legend.appendChild(anchor);

        // Put a wrapper around the fieldset contents for ease
        // of hiding.
        var wrapper_div = Y.Node.create(
            '<div class="collapseWrapper" />');

        // Loop over the children of the collapsible and move them
        // into the wrapper div. We remove the legend from the
        // collapsible at this point to make sure it gets left
        // outside the wrapper div; we'll add it again later.
        collapsible.removeChild(legend);

        // "Why do this as a while?" I hear you cry. Well, it's
        // because using Y.each() leads to interesting results
        // in FF3.5, Opera and Chrome, since by doing
        // appendChild() with each child node (and thus removing
        // them from the collapsible) means you're altering the
        // collection as you're looping over it, which is a Bad
        // Thing. This isn't as pretty but it actually works.
        var first_child = collapsible.one(':first-child');
        while (Y.Lang.isValue(first_child)) {
            wrapper_div.appendChild(first_child);
            first_child = collapsible.one(':first-child');
        }

        // Put the legend and the new wrapper div into the
        // collapsible in the right order.
        collapsible.appendChild(legend);
        collapsible.appendChild(wrapper_div);

        // If the collapsible is to be collapsed on pageload, do
        // so.
        if (collapsible.hasClass('collapsed')) {
            // Strip out the 'collapsed' class as it's no longer
            // needed.
            collapsible.removeClass('collapsed'); 
            // We use the slide_in effect to hide the
            // collapsible because it sets up all the properties
            // and classes for the element properly and saves us
            // from embarrasment later on.
            var slide_in = Y.lazr.effects.slide_in(wrapper_div);
            slide_in.run();

            icon.set('src', '/@@/treeCollapsed');
        }

        // Finally, add toggle_collapsible() as an onclick
        // handler to the anchor.
        anchor.on('click', function(e) {
            Y.lp.toggle_collapsible(collapsible);
        });
    });
}
}, '0.1', {requires: [
    'node', 'lazr.anim', 'lp']});
