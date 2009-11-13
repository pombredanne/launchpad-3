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

YUI({
    base: '../../yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('lazr.error', 'lazr.testing.runner', 'node', 'event', 'yuitest', 'console', function(Y) {

var suite = new Y.Test.Suite('Lazr-js error Test Suite');

suite.add(new Y.Test.Case({

    name: 'error_basics',

    setUp: function() {},
    tearDown: function() {},

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
