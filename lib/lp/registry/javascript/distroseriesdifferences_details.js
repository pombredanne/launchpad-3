/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Enhancements for the distroseries differences page.
 *
 * @module registry
 * @submodule distroseriesdifferences_details
 * @requires  event, node, oop
 */
YUI.add('lp.registry.distroseriesdifferences_details', function(Y) {

var namespace = Y.namespace('lp.registry.distroseriesdifferences_details');

/*
 * Setup the expandable rows for each difference.
 *
 * @method setup_expandable_rows
 */
namespace.setup_expandable_rows = function() {
    function expander_handler(e) {
        e.preventDefault();
        var toggle = e.currentTarget;
        var row = toggle.ancestor('tr');
        toggle.toggleClass('treeCollapsed').toggleClass('treeExpanded');

        // Only insert if there isn't already a container row there.
        next_row = row.next();
        if (next_row == null || !next_row.hasClass('diff-extra')) {
            details_row = Y.Node.create(
                '<table><tr colspan="5" class="diff-extra unseen"><td>hey</td></tr></table>').one('tr');
            row.insert(details_row, 'after');
        } else {
            details_row = next_row
        }

        details_row.toggleClass('unseen');

    }
    Y.all('table.listing a.toggle-extra').each(function(toggle){
        toggle.addClass('treeCollapsed').addClass('sprite');
        toggle.on("click", expander_handler);
    })

};

}, "0.1", {"requires": ["oop", "node", "event"]});
