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

    var unblacklist_handler = function(e, api_uri, source_name) {
        e.preventDefault();
        var blacklist_options_container = this;
        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Removing from blacklist.');

        blacklist_options_container.insert(in_progress_message, 'replace');

        var config = {
            on: {
                success: function() {
                    add_blacklist_options_handler(
                        blacklist_options_container, source_name);
                    var diff_rows = Y.all('tr.' + source_name);
                    Y.each(diff_rows, function(diff_row) {
                        var fade_from_gray = new Y.Anim({
                            node: diff_row,
                            to: { backgroundColor: '#FFFFFF'},
                            });
                        fade_from_gray.run();
                        });
                    },
                failure: function(id, response) {

                    }
                },
            //accept: LP.client.XHTML
            };

        lp_client.named_post(api_uri, 'unblacklist', config);
    };

    var blacklist_handler = function(e, api_uri, source_name) {
        e.preventDefault();
        var blacklist_options_container = this.ancestor('div');
        var blacklist_all = false;

        var in_progress_str = ['Blacklisting until a new version ',
                               'is published.'].join('');
        var success_msg = [
            'This difference has been blacklisted until a new version ',
            'is published.'
            ].join('');
        if (e.target.hasClass('blacklist-all')) {
            blacklist_all = true;
            in_progress_str = 'Blacklisting all future versions.';
            success_msg = 'This difference has been blacklisted permanently.';
        }

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            in_progress_str)
        var blacklist_options = blacklist_options_container.removeChild(
            blacklist_options_container.one('div.blacklist-options'));
        blacklist_options_container.insert(in_progress_message, 'replace');

        var diff_rows = Y.all('tr.' + source_name);

        var config = {
            on: {
                success: function(updated_entry, args) {
                    blacklist_options_container.insert(
                        success_msg, 'replace');
                    blacklist_options_container.append(
                        ' <a href="#" class="js-action">Undo</a>');
                    Y.on('click', unblacklist_handler,
                         blacklist_options_container.all('a'),
                         blacklist_options_container, api_uri,
                         source_name);

                    // Let the use know this item is now blacklisted.
                    Y.lazr.anim.green_flash({
                        node: success_msg}).run();
                    Y.each(diff_rows, function(diff_row) {
                        var fade_to_gray = new Y.Anim({
                            node: diff_row,
                            to: { backgroundColor: '#EEEEEE'},
                            });
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

        lp_client.named_post(api_uri, 'blacklist', config);

    };

    /**
     * Link the click event for these blacklist options to the correct
     * api uri.
     *
     * @param blacklist_options {Node} The node containing the blacklist
     *                          options.
     * @param source_name {string} The name of the source to update.
     */
    var add_blacklist_options_handler = function(blacklist_options,
                                                 source_name) {
        var api_uri = [
            LP.client.cache.context.self_link,
            '+difference',
            source_name
            ].join('/')
        Y.on('click', blacklist_handler, blacklist_options.all('a'),
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
            add_blacklist_options_handler(args.container.one(
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
