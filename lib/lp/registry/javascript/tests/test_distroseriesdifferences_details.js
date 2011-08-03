/* Copyright 2009 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI().use(
        'lp.testing.runner', 'test', 'console', 'node-event-simulate',
        'lp.soyuz.base', "lazr.anim", "lazr.effects",
        'lp.soyuz.dynamic_dom_updater', 'event-simulate', "io-base",
        'lp.registry.distroseriesdifferences_details', function(Y) {

var suite = new Y.Test.Suite("Distroseries differences Tests");
var dsd_details = Y.lp.registry.distroseriesdifferences_details;
var dsd_uri = '/duntu/dwarty/+source/evolution/+difference/ubuntu/warty';

var table_html = [
    '<table class="listing"><tbody>',
    '  <tr class="evolution">',
    '    <td>',
    '      <a href="/deribuntu/deriwarty/+source/evolution/+difference/ubuntu/warty"',
    '         class="js-action toggle-extra treeCollapsed ',
    '         sprite">evolution</a>',
    '    </td>',
    '    <td>',
    '      <a href="/ubuntu/warty" class="parent-name">Warty</a>',
    '    </td>',
    '    <td>',
    '      <a href="/ubuntu/warty/+source/evolution/2.0.9-1ubuntu2"',
    '         class="parent-version">',
    '         2.0.9-1ubuntu2</a>',
    '    </td>',
    '    <td>',
    '      <a href="/deribuntu/deriwarty/+source/evolution/2.0.8-4deribuntu1"',
    '         class="derived-version">',
    '         2.0.8-4deribuntu1</a>',
    '    </td>',
    '    <td class="packagesets"></td>',
    '    <td class="last-changed"></td>',
    '    <td class="latest-comment-fragment"></td>',
    '  </tr>',
    '</tbody></table>'
    ].join('');


var testExpandableRowWidget = {

    name: 'expandable-row-widget',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(table_html));
        this.toggle = Y.one('table.listing a.toggle-extra');
     },

    test_initializer: function() {
       var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
       Y.Assert.isTrue(this.toggle.hasClass('treeCollapsed'));
       Y.Assert.isTrue(this.toggle.hasClass('sprite'));
    },

    test_parse_row_data: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        var parsed = row.parse_row_data();
        var res = {
            source_name: 'evolution',
            parent_series_name: 'warty',
            parent_distro_name: 'ubuntu',
            nb_columns: 7};
        Y.ObjectAssert.areEqual(res, parsed);
    },

    test_expander_handler: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        row._toggle.simulate('click');
        var new_row = row._row.next();
        Y.Assert.isTrue(new_row.hasClass('evolution'));
        Y.Assert.isTrue(new_row.hasClass('diff-extra'));
        Y.Assert.areEqual(7, new_row.one('td').getAttribute('colspan'));
    },

    test_expand_handler_toggles_hiding: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        Y.Assert.isTrue(row._toggle.hasClass('treeCollapsed'));
        // First click opens up the new row.
        row._toggle.simulate('click');
        var new_row = row._row.next();
        Y.Assert.isTrue(row._toggle.hasClass('treeExpanded'));
        Y.Assert.isFalse(new_row.hasClass('unseen'));
        // Second click hides it.
        row._toggle.simulate('click');
        Y.Assert.isTrue(row._toggle.hasClass('treeCollapsed'));
        Y.Assert.isTrue(new_row.hasClass('unseen'));
    }

};

var extra_table_html = [
    '<table class="listing">',
    '  <tbody><tr><td>',
    '    <div class="diff-extra-container">',
    '      <input name="field.selected_differences" type="checkbox" />',
    '      <a class="toggle-extra"',
    '        href="/deribuntu/deriwarty/+source/evolution/+difference/ubuntu/warty">',
    '        evolution</a>',
    '      <span class="package-diff-button"></span>',
    '      <dt class="package-diff-placeholder">',
    '       <span class="package-diff-compute-request">',
    '        <a class="js-action sprite add" href="">',
    '          Compute differences from last common version:',
    '        </a>',
    '      </span></dt>',
    '      <dd>',
    '        <ul class="package-diff-status">',
    '          <li>',
    '            <span id="derived" class="PENDING">',
    '             1.2.1 to Derilucid version: 1.2.4',
    '            </span>',
    '          </li>',
    '          <li>',
    '            <span id="parent" class="request-derived-diff">',
    '              1.2.1 to Lucid version: 1.2.3',
    '            </span>',
    '          </li>',
    '        </ul>',
    '      </dd>',
    '    </div>',
    '  </td></tr></tbody>',
    '</table>'
    ].join('');

var testPackageDiffUpdate = {

    name: 'package-diff',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(extra_table_html));
    },

    test_vocabulary_helper: function() {
        // The vocabulary helper extracts the selected item from a
        // jsonified vocabulary.
        var voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        var res = dsd_details.get_selected(voc);
        Y.Assert.areEqual('COMPLETED', res.token);
        Y.Assert.areEqual('Completed', res.title);
        var voc_nothing_selected = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        Y.Assert.isUndefined(dsd_details.get_selected(voc_nothing_selected));
    },

    test_add_msg_node: function() {
        var msg_txt = 'Exemple text';
        var msg_node = Y.Node.create(msg_txt);
        placeholder = Y.one('#placeholder');
        dsd_details.add_msg_node(placeholder, msg_node);
        Y.Assert.areEqual(
            placeholder.one('.package-diff-placeholder').get('innerHTML'),
            msg_txt);
    }
};


var testPackageDiffUpdateInteraction = {

    name: 'package-diff-update-interaction',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(extra_table_html));
        var first_poll = true;
        pending_voc = [
            {"token": "PENDING", "selected": true, "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        completed_voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];

        // Monkey patch request.
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            config.on.success();};
        lp_prot.named_get = function(url, func, config) {
            config.on.success();};
        lp_prot.get = function(uri, config) {
            if (first_poll === true) {
                first_poll = false;
                config.on.success(pending_voc);
            }
            else {
                config.on.success(completed_voc);
            }
        };
        dsd_details.poll_interval = 100;
    },

    test_request_wrong_click: function() {
        // Click on the placeholder has no effect.
        // The listeners are on the the link with class
        // '.package-diff-compute-request'.
        // bug=746277.
        var placeholder = Y.one('#placeholder');
        placeholder
            .one('#derived')
                .removeClass('PENDING')
                    .addClass('FAILED');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var func_req;
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var wrong_button = placeholder.one('.package-diff-placeholder');

        wrong_button.simulate('click');
        var package_diff = Y.one('#parent');

        // The request has not been triggered.
        Y.Assert.isTrue(package_diff.hasClass('request-derived-diff'));
    },

    test_request_package_diff_computation: function() {
        // A click on the button changes the package diff status and requests
        // the package diffs computation via post.
        var placeholder = Y.one('#placeholder');
        placeholder
            .one('#derived')
            .removeClass('PENDING')
            .addClass('FAILED');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var func_req;
        var lp_prot = Y.lp.client.Launchpad.prototype;
        lp_prot.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var button = placeholder.one('.package-diff-compute-request');

        button.simulate('click');
        var package_diff = Y.one('#parent');

        Y.Assert.isTrue(package_diff.hasClass('PENDING'));
        Y.Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        Y.Assert.areEqual('requestPackageDiffs', func_req);
        Y.Assert.isNotUndefined(package_diff.updater);

        // Let the polling happen.
        this.wait(function() {
            Y.Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Y.Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, dsd_details.poll_interval);
         }, dsd_details.poll_interval);
    },

    test_polling_for_pending_items: function() {
        // The polling has started on the pending package diff. The
        // status is being updated.
        var placeholder = Y.one('#placeholder');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var package_diff = Y.one('#derived');
        Y.Assert.isTrue(package_diff.hasClass('PENDING'));
        Y.Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        this.wait(function() {
            Y.Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Y.Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, dsd_details.poll_interval);
        }, dsd_details.poll_interval);
    }
};

suite.add(new Y.Test.Case(testPackageDiffUpdate));
suite.add(new Y.Test.Case(testPackageDiffUpdateInteraction));
suite.add(new Y.Test.Case(testExpandableRowWidget));

Y.lp.testing.Runner.run(suite);

});

