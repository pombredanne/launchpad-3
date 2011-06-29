/*
    Copyright (c) 2009, Canonical Ltd.  All rights reserved.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

YUI().use('lazr.error', 'lazr.error.minimal-error-widget',
          'lazr.testing.runner', 'node', 'event', 'test',
          'console', function(Y) {

var suite = new Y.Test.Suite('Lazr-js error Test Suite');

suite.add(new Y.Test.Case({

    name: 'error_basics',

    setUp: function() {
        Y.lazr.error.widget = undefined;
    },

    test_display_error_creates_basic_error_widget: function() {
        // A basic error widget will be created if the error
        // widget is undefined.
        Y.Assert.isUndefined(Y.lazr.error.widget);
        Y.lazr.error.display_error("Error 1234567890");
        Y.Assert.isInstanceOf(
            Y.lazr.error_widgets.BasicErrorWidget , Y.lazr.error.widget);
    },
    test_display_error_calls_showError: function() {
        Y.lazr.error.widget = Y.Mock();
        var error_message = "Error 1234567890";
        Y.Mock.expect(
            Y.lazr.error.widget, {
                method: "showError",
                args: [error_message]});
        Y.lazr.error.display_error(error_message);
        Y.Mock.verify(Y.lazr.error.widget);
    }
}));


suite.add(new Y.Test.Case({

    name: 'basicerrorwidget_tests',

    setUp: function() {
        Y.lazr.error.widget = new Y.lazr.error_widgets.BasicErrorWidget();
        Y.lazr.error.widget.render();
    },

    test_widget_adds_error: function() {
        Y.Assert.areEqual(
            0, Y.lazr.error.widget.error_list.length);
        Y.lazr.error.widget.showError('Hey there.');
        Y.Assert.areEqual(
            1, Y.lazr.error.widget.error_list.length);
        Y.Assert.areEqual(
            'Hey there.', Y.lazr.error.widget.error_list[0]);
    }
}));

suite.add(new Y.Test.Case({

    name: 'minimalerrorwidget_tests',

    setUp: function() {
        var widget_module = Y.lazr.error.minimal_error_widget;
        Y.lazr.error.widget = new widget_module.MinimalErrorWidget();
        Y.lazr.error.widget.render();
    },

    test_widget_adds_error: function() {
        Y.Assert.areEqual(
            0, Y.lazr.error.widget.error_list.length);
        Y.lazr.error.widget.showError('Hey there.');
        Y.Assert.areEqual(
            1, Y.lazr.error.widget.error_list.length);
        Y.Assert.areEqual(
            'Hey there.', Y.lazr.error.widget.error_list[0]);
    }
}));


Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
