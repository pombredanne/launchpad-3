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
        var blacklist_options_container = this;
        var blacklist_all = false;

        // XXX - move all blacklist options/text generation to
        // template fragment.
        var in_progress_msg = ['Blacklisted until a new version ',
                               'is published.'].join('');
        var success_msg = 'Blacklisted until a new version is published.';
        if (e.target.hasClass('blacklist-all')) {
            blacklist_all = true;
            in_progress_msg = 'Blacklisting all future versions.';
            success_msg = 'Blacklisted permanently.';
        }
        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            in_progress_msg)
        var blacklist_options = blacklist_options_container.removeChild(
            blacklist_options_container.one('div'));
        blacklist_options_container.insert(in_progress_message, 'replace');

        var diff_rows = Y.all('tr.' + source_name);

        var config = {
            on: {
                success: function(updated_entry, args) {
                    Y.each(diff_rows, function(diff_row) {
                        var fade_to_gray = new Y.Anim({
                            node: diff_row,
                            to: { backgroundColor: '#EEEEEE'},
                            });
                        fade_to_gray.run();
                        });

                    blacklist_options_container.insert(
                        success_msg, 'replace');
                    Y.lazr.anim.green_flash({
                        node:success_msg}).run();
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

        // The context passed when this event was created is a simple
        // object with the uri.
        lp_client.named_post(api_uri, 'blacklist', config);

    }
    var setup_blacklist_options = function(container, source_name, source_version) {
        var blacklist_options = Y.Node.create([
            '<div>',
            '  <a href="#" class="js-action blacklist-all">Blacklist ',
            '     all versions of ' + source_name,
            '  </a><br/>',
            '  <a href="#" class="js-action blacklist-version">Blacklist ' + source_name,
            ' ' + source_version + '</a>',
            '</div>',
            ].join(''));
        container.insert(blacklist_options, 'replace')
        var api_uri = [
            LP.client.cache.context.self_link,
            '+difference',
            source_name
            ].join('/')
        Y.on('click', blacklist_handler, blacklist_options.all('a'),
             container, api_uri, source_name);
    };

    var start_update = function(uri, container, source_name, source_version) {

        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Fetching difference details ...')
        container.one('div.diff-extra-container').insert(
            in_progress_message, 'replace');

        var config = {
            on: {
                'success': function(transaction_id, response, args) {
                    args.container.one(
                        'div.diff-extra-container').insert(
                            response.responseText, 'replace');
                    setup_blacklist_options(args.container.one(
                        'div.blacklist-options'), source_name,
                        source_version);
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
            var source_name = row.one('a.toggle-extra').get('text');
            var details_row = Y.Node.create([
                '<table><tr class="diff-extra unseen ' + source_name + '">',
                '  <td colspan="5">',
                '    <div class="blacklist-options" style="float:right"></div>',
                '    <div class="diff-extra-container"></div>',
                '  </td></tr></table>'
                ].join('')).one('tr');
            row.insert(details_row, 'after');
            var uri = toggle.get('href');
            var version = row.one('a.derived-version').get('text');
            start_update(uri, details_row.one('td'), source_name, version);
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
