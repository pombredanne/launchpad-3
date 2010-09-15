/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Enhancements for the distroseries differences page.
 *
 * @module registry
 * @submodule distroseriesdifferences_details
 * @requires  io-base, lp.soyuz.base
 */
YUI.add('lp.registry.distroseriesdifferences_details', function(Y) {

var namespace = Y.namespace('lp.registry.distroseriesdifferences_details');

/*
 * Setup the expandable rows for each difference.
 *
 * @method setup_expandable_rows
 */
namespace.setup_expandable_rows = function() {
    var start_update = function(uri, container) {

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Fetching difference details ...')
        container.insert(in_progress_message, 'replace');

        var config = {
            on: {
                'success': function(transaction_id, response, args) {
                    args.container.set(
                        'innerHTML', response.responseText);
                        // Change to insert(,'replace)
                    },
                'failure': function(transaction_id, response, args){
                       var retry_handler = function(e) {
                           e.preventDefault();
                           start_update(args.uri, args.container);
                           };
                       var failure_message = Y.lp.soyuz.base.makeFailureNode(
                           'Failed to fetch difference details.',
                           retry_handler);
                       args.container.insert(failure_message, 'replace');

                       var anim = Y.lazr.anim.red_flash({
                            node: args.container
                            });
                       anim.run();
                }
            },
            arguments: {
                'container': container,
                'uri': uri
            }
        };
        Y.io(uri, config);

    };

    var expander_handler = function(e) {
        e.preventDefault();
        var toggle = e.currentTarget;
        var row = toggle.ancestor('tr');
        toggle.toggleClass('treeCollapsed').toggleClass('treeExpanded');

        // Only insert if there isn't already a container row there.
        next_row = row.next();
        if (next_row == null || !next_row.hasClass('diff-extra')) {
            details_row = Y.Node.create(
                '<table><tr class="diff-extra unseen"><td colspan="5"></td></tr></table>').one('tr');
            row.insert(details_row, 'after');
            var uri = toggle.get('href');
            start_update(uri, details_row.one('td'));
        } else {
            details_row = next_row
        }

        details_row.toggleClass('unseen');

    };
    Y.all('table.listing a.toggle-extra').each(function(toggle){
        toggle.addClass('treeCollapsed').addClass('sprite');
        toggle.on("click", expander_handler);
    })

};

}, "0.1", {"requires": ["io-base", "lp.soyuz.base"]});
