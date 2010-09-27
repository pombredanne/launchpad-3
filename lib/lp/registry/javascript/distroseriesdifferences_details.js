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

/**
 * Create one Launchpad client that will be used with multiple requests.
 */
var lp_client = new LP.client.Launchpad();

/*
 * Setup the expandable rows for each difference.
 *
 * @method setup_expandable_rows
 */
namespace.setup_expandable_rows = function() {

    var blacklist_handler = function(e, api_uri, source_name) {
        e.preventDefault();
        var blacklist_options_container = this.ancestor('div');

        // Disable all the inputs
        blacklist_options_container.all('input').set('disabled', 'disabled');

        var method_name = 'blacklist';
        var blacklist_all = false;
        var in_progress_str = ['Blacklisting until a new version ',
                               'is published.'].join('');

        if (e.target.get('value') == 'BLACKLISTED_ALWAYS') {
            blacklist_all = true;
            in_progress_str = 'Blacklisting all future versions.';
        } else if (e.target.get('value') == 'NONE') {
            method_name = 'unblacklist';
        }

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            in_progress_str)
        blacklist_options_container.one('div.inprogress_msg').insert(
            in_progress_message, 'replace');

        var diff_rows = Y.all('tr.' + source_name);

        var config = {
            on: {
                success: function(updated_entry, args) {
                    // Let the use know this item is now blacklisted.
                    blacklist_options_container.all(
                        'input').set('disabled', false);
                    blacklist_options_container.one(
                        'div.inprogress_msg p').remove();
                    Y.lazr.anim.green_flash({
                        node: blacklist_options_container.one('div')}).run();
                    Y.each(diff_rows, function(diff_row) {
                        var fade_to_gray = new Y.Anim({
                            node: diff_row,
                            from: { backgroundColor: '#FFFFFF'},
                            to: { backgroundColor: '#EEEEEE'}
                            });
                        if (method_name == 'unblacklist') {
                            fade_to_gray.set('reverse', true);
                            }
                        fade_to_gray.run();
                        });
                },
                failure: function(id, response) {
                    blacklist_options_container.insert(
                        blacklist_options, 'replace');
                }
            },
            parameters: {
                all: blacklist_all
            }
        };

        lp_client.named_post(api_uri, method_name, config);

    };

    /**
     * Link the click event for these blacklist options to the correct
     * api uri.
     *
     * @param blacklist_options {Node} The node containing the blacklist
     *                          options.
     * @param source_name {string} The name of the source to update.
     */
    var setup_blacklist_options = function(blacklist_options,
                                                 source_name) {
        var api_uri = [
            LP.client.cache.context.self_link,
            '+difference',
            source_name
            ].join('/')
        Y.on('change', blacklist_handler, blacklist_options.all('input'),
             blacklist_options, api_uri, source_name);
    };

    /**
     * Get the extra information for this diff to display.
     *
     * @param uri {string} The uri for the extra diff info.
     * @param container {Node} A node which must contain a div with the
     *                  class 'diff-extra-container' into which the results
     *                  are inserted.
     */
    var get_extra_diff_info = function(uri, container, source_name) {

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Fetching difference details ...')
        container.one('div.diff-extra-container').insert(
            in_progress_message, 'replace');

        var success_cb = function(transaction_id, response, args) {
            args.container.one('div.diff-extra-container').insert(
                response.responseText, 'replace');
            setup_blacklist_options(args.container.one(
                'div.blacklist-options'), source_name);
            };

        var failure_cb = function(transaction_id, response, args){
           var retry_handler = function(e) {
               e.preventDefault();
               get_extra_diff_info(args.uri, args.container);
               };
           var failure_message = Y.lp.soyuz.base.makeFailureNode(
               'Failed to fetch difference details.',
               retry_handler);
           args.container.insert(failure_message, 'replace');

           var anim = Y.lazr.anim.red_flash({
                node: args.container
                });
           anim.run();
           };

        var config = {
            on: {
                'success': success_cb,
                'failure': failure_cb,
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
            var source_name = row.one('a.toggle-extra').get('text');
            var details_row = Y.Node.create([
                '<table><tr class="diff-extra unseen ' + source_name + '">',
                '  <td colspan="5">',
                '    <div class="diff-extra-container"></div>',
                '  </td></tr></table>'
                ].join('')).one('tr');
            row.insert(details_row, 'after');
            var uri = toggle.get('href');
            get_extra_diff_info(uri, details_row.one('td'), source_name);
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

}, "0.1", {"requires": ["io-base", "lp.soyuz.base", "lazr.anim"]});
