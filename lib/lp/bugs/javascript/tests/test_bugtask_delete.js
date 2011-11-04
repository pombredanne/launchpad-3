YUI().use('lp.testing.runner', 'lp.testing.mockio', 'base', 'test', 'console',
          'node', 'node-event-simulate', 'lp.bugs.bugtask_index',
    function(Y) {

var suite = new Y.Test.Suite("Bugtask deletion Tests");
var module = Y.lp.bugs.bugtask_index;


suite.add(new Y.Test.Case({
    name: 'Bugtask delete',

        setUp: function() {
            module.ANIM_DURATION = 0;
            this.link_conf = {
                row_id: 'tasksummary49',
                form_row_id: 'tasksummary49',
                user_can_delete: true
            };
            window.LP = {
                links: {me : "/~user"},
                cache: {
                    bugtask_data: {49: this.link_conf}
                }
            };
            this.fixture = Y.one('#fixture');
            var bugtasks_table = Y.Node.create(
                    Y.one('#form-template').getContent());
            this.fixture.appendChild(bugtasks_table);
            this.delete_link = bugtasks_table.one('#bugtask-delete-task49');
        },

        tearDown: function() {
            if (this.fixture !== null) {
                this.fixture.empty();
            }
            Y.one('#request-notifications').empty();
            delete this.fixture;
            delete window.LP;
        },

        test_show_spinner: function() {
            // Test the delete progress spinner is shown.
            module._showDeleteSpinner(this.delete_link);
            Y.Assert.isNotNull(this.fixture.one('.spinner'));
            Y.Assert.isTrue(this.delete_link.hasClass('unseen'));
        },

        test_hide_spinner: function() {
            // Test the delete progress spinner is hidden.
            module._showDeleteSpinner(this.delete_link);
            module._hideDeleteSpinner(this.delete_link);
            Y.Assert.isNull(this.fixture.one('.spinner'));
            Y.Assert.isFalse(this.delete_link.hasClass('unseen'));
        },

        _test_delete_confirmation: function(click_ok) {
            // Test the delete confirmation dialog when delete is clicked.
            var orig_delete_bugtask = module.delete_bugtask;

            var delete_called = false;
            var self = this;
            module.delete_bugtask = function(delete_link, conf) {
                Y.Assert.areEqual(self.delete_link, delete_link);
                Y.Assert.areEqual(self.link_conf, conf);
                delete_called = true;
            };
            module.setup_bugtask_table();
            this.delete_link.simulate('click');
            var co = Y.one('.yui3-overlay.yui3-lp-app-confirmationoverlay');
            var actions = co.one('.yui3-lazr-formoverlay-actions');
            var btn_style;
            if (click_ok) {
                btn_style = '.ok-btn';
            } else {
                btn_style = '.cancel-btn';
            }
            var button = actions.one(btn_style);
            button.simulate('click');
            Y.Assert.areEqual(click_ok, delete_called);
            Y.Assert.isTrue(
                    co.hasClass('yui3-lp-app-confirmationoverlay-hidden'));
            module.delete_bugtask = orig_delete_bugtask;
        },

        test_delete_confirmation_ok: function() {
            // Test the delete confirmation dialog Ok functionality.
            this._test_delete_confirmation(true);
        },

        test_delete_confirmation_cancel: function() {
            // Test the delete confirmation dialog Cancel functionality.
            this._test_delete_confirmation(false);
        },

        test_setup_bugtask_table: function() {
            // Test that the bugtask table is wired up, the pickers and the
            // delete links etc.
            var namespace = Y.namespace('lp.app.picker.connect');
            var connect_picker_called = false;
            namespace['show-widget-product'] = function() {
                connect_picker_called = true;
            };
            var orig_confirm_bugtask_delete = module._confirm_bugtask_delete;
            var self = this;
            var confirm_delete_called = false;
            module._confirm_bugtask_delete = function(delete_link, conf) {
                Y.Assert.areEqual(self.delete_link, delete_link);
                Y.Assert.areEqual(self.link_conf, conf);
                confirm_delete_called = true;
            };
            module.setup_bugtask_table();
            this.delete_link.simulate('click');
            Y.Assert.isTrue(connect_picker_called);
            Y.Assert.isTrue(confirm_delete_called);
            module._confirm_bugtask_delete = orig_confirm_bugtask_delete;
        },

        test_render_bugtask_table: function() {
            // Test that a new bug task table is rendered and setup.
            var orig_setup_bugtask_table = module.setup_bugtask_table;
            var setup_called = false;
            module.setup_bugtask_table = function() {
                setup_called = true;
            };
            var test_table =
                '<table id="affected-software">'+
                '<tr><td>foo</td></tr></table>';
            module._render_bugtask_table(test_table);
            Y.Assert.isTrue(setup_called);
            Y.Assert.areEqual(
                '<tbody><tr><td>foo</td></tr></tbody>',
                this.fixture.one('table#affected-software').getContent());
            module.setup_bugtask_table = orig_setup_bugtask_table;
        },

        test_process_bugtask_delete_redirect_response: function() {
            // Test the processing of a XHR delete result which is to
            // redirect the browser to a new URL.
            var orig_redirect = module._redirect;
            var redirect_called = false;
            module._redirect = function(url) {
                Y.Assert.areEqual('http://foo', url);
                redirect_called = true;
            };
            var response = new Y.lp.testing.mockio.MockHttpResponse({
                responseText: '{"bugtask_url": "http://foo"}',
                responseHeaders: {'Content-type': 'application/json'}});
            module._process_bugtask_delete_response(
                response, this.link_conf.row_id);
            this.wait(function() {
                // Wait for the animation to complete.
                Y.Assert.isTrue(redirect_called);
            }, 50);
            module._redirect = orig_redirect;
        },

        test_process_bugtask_delete_new_table_response: function() {
            // Test the processing of a XHR delete result which is to
            // replace the current bugtasks table.
            var orig_render_bugtask_table = module._render_bugtask_table;
            var render_table_called = false;
            module._render_bugtask_table = function(new_table) {
                Y.Assert.areEqual('<table>Foo</table>', new_table);
                render_table_called = true;
            };
            var notifications = '[ [20, "Delete Success"] ]';
            var response = new Y.lp.testing.mockio.MockHttpResponse({
                responseText: '<table>Foo</table>',
                responseHeaders: {
                    'Content-type': 'text/html',
                    'X-Lazr-Notifications': notifications}});
            module._process_bugtask_delete_response(
                response, this.link_conf.row_id);
            this.wait(function() {
                // Wait for the animation to complete.
                Y.Assert.isTrue(render_table_called);
                var node = Y.one('div#request-notifications ' +
                                    'div.informational.message');
                Y.Assert.areEqual('Delete Success', node.getContent());
            }, 50);
            module._render_bugtask_table = orig_render_bugtask_table;
        },

        test_delete_bugtask: function() {
            // Test that when delete_bugtask is called, the expected XHR call
            // is made.
            var orig_delete_repsonse =
                module._process_bugtask_delete_response;

            var delete_response_called = false;
            var self = this;
            module._process_bugtask_delete_response = function(response, id) {
                Y.Assert.areEqual('<p>Foo</p>', response.responseText);
                Y.Assert.areEqual(self.link_conf.row_id, id);
                delete_response_called = true;
            };

            var mockio = new Y.lp.testing.mockio.MockIo();
            var conf = Y.merge(this.link_conf, {io_provider: mockio});
            module.delete_bugtask(this.delete_link, conf);
            mockio.success({
                responseText: '<p>Foo</p>',
                responseHeaders: {'Content-Type': 'text/html'}});
            // Check the parameters passed to the io call.
            Y.Assert.areEqual(
                this.delete_link.get('href'),
                mockio.last_request.url);
            Y.Assert.areEqual(
                'POST', mockio.last_request.config.method);
            Y.Assert.areEqual(
                'application/json; application/xhtml',
                mockio.last_request.config.headers.Accept);
            Y.Assert.areEqual(
                'field.actions.delete_bugtask=Delete',
                mockio.last_request.config.data);
            Y.Assert.isTrue(delete_response_called);

            module._process_bugtask_delete_response = orig_delete_repsonse;
        }
}));

Y.lp.testing.Runner.run(suite);
});
