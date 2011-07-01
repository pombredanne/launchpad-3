/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lazr.anim', 'lazr.testing.runner', 'node',
          'event', 'event-simulate', 'console', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("Anim Tests");

suite.add(new Y.Test.Case({

    name: 'anim_basics',

    setUp: function() {
        this.workspace = Y.one('#workspace');
        if (!this.workspace){
            Y.one(document.body).appendChild(Y.Node.create(
                '<div id="workspace">'
                + '<table id="anim-table">'
                + '<tr id="anim-table-tr">'
                + '<td id="anim-table-td1" style="background: #eeeeee">foo</td>'
                + '<td id="anim-table-td2" style="background: #eeeeee">bar</td>'
                + '</tr></table></div>'));
            this.workspace = Y.one('#workspace');
        }
    },

    tearDown: function() {
        this.workspace.get('parentNode').removeChild(this.workspace);
    },

    test_resolveNodeListFrom_selector: function() {
        var nodelist = Y.lazr.anim.resolveNodeListFrom('#anim-table-td1');
        var nodelist_nodes = (nodelist._nodes !== undefined);
        Assert.isTrue(nodelist_nodes, 'Not a nodelist from a selector');
    },

    test_resolveNodeListFrom_node: function() {
        var node = Y.one('#anim-table-td1');
        var nodelist = Y.lazr.anim.resolveNodeListFrom(node);
        var nodelist_nodes = (nodelist._nodes !== undefined);
        Assert.isTrue(nodelist_nodes, 'Not a nodelist from a Node');
    },

    test_resolveNodeListFrom_node_list: function() {
        var nodelist = Y.all('#anim-table td');
        var nodelist = Y.lazr.anim.resolveNodeListFrom(nodelist);
        var nodelist_nodes = (nodelist._nodes !== undefined);
        Assert.isTrue(nodelist_nodes, 'Not a nodelist from a NodeList');
    },

    test_resolveNodeListFrom_anythine_else: function() {
        var succeed = true;
        try {
            var nodelist = Y.lazr.anim.resolveNodeListFrom(
                {crazy: true, broken: 'definitely'});
        } catch(e) {
            succeed = false;
        }
        Assert.isFalse(succeed, "Somehow, we're cleverer than we thought.");
    },

    test_green_flash_td1: function() {
        // works as expected on a single node,
        // without coercion into a NodeList here
        var node = Y.one('#anim-table-td1');
        var bgcolor = node.getStyle('backgroundColor');
        var anim = Y.lazr.anim.green_flash(
            {node: node,
             to: {backgroundColor: bgcolor},
             duration: 0.2}
        );
        anim.run();
        this.wait(function() {
            Assert.areEqual(
                bgcolor,
                node.getStyle('backgroundColor'),
                'background colors do not match'
                );
            }, 500
        );
    },

    test_green_flash_td1_by_selector: function() {
        // works as expected on a single node selector,
        // without coercion into a NodeList here
        var node = Y.one('#anim-table-td1');
        var bgcolor = node.getStyle('backgroundColor');
        var anim = Y.lazr.anim.green_flash(
            {node: '#anim-table-td1',
             to: {backgroundColor: bgcolor},
             duration: 0.2}
        );
        anim.run();
        this.wait(function() {
            Assert.areEqual(
                bgcolor,
                node.getStyle('backgroundColor'),
                'background colors do not match'
                );
            }, 500
        );
    },

    test_green_flash_multi: function() {
        // works with a native NodeList as well
        var nodelist = Y.all('#anim-table td');
        var red = '#ff0000';
        var backgrounds = [];
        Y.each(nodelist, function(n) {
                   backgrounds.push({bg: n.getStyle('backgroundColor'), node: n});
               });
        var anim = Y.lazr.anim.green_flash(
            {node: nodelist,
             to: {backgroundColor: red},
             duration: 5}
        );
        anim.run();
        this.wait(function() {
                Assert.areNotEqual(
                    backgrounds[0].node.getStyle('backgroundColor'),
                    red,
                    'background of 0 has mysteriously jumped to the end color.'
                );
                Assert.areNotEqual(
                    backgrounds[1].node.getStyle('backgroundColor'),
                    red,
                    'background of 1 has mysteriously jumped to the end color.'
                );
                Assert.areNotEqual(
                    backgrounds[0].node.getStyle('backgroundColor'),
                    backgrounds[0].bg,
                    'background of 0 has not changed at all.'
                );
                Assert.areNotEqual(
                    backgrounds[1].node.getStyle('backgroundColor'),
                    backgrounds[1].bg,
                    'background of 1 has not changed at all.'
                );
            }, 1500
        );
    },

    test_green_flash_multi_by_selector: function() {
        // works with a native NodeList as well
        var nodelist = Y.all('#anim-table td');
        var red = '#ff0000';
        var backgrounds = [];
        Y.each(nodelist, function(n) {
                   backgrounds.push({bg: n.getStyle('backgroundColor'), node: n});
               });
        var anim = Y.lazr.anim.green_flash(
            {node: '#anim-table td',
             to: {backgroundColor: red},
             duration: 2}
        );
        anim.run();
        this.wait(function() {
                Assert.areNotEqual(
                    backgrounds[0].node.getStyle('backgroundColor'),
                    red,
                    'background of 0 has mysteriously jumped to the end color.'
                );
                Assert.areNotEqual(
                    backgrounds[1].node.getStyle('backgroundColor'),
                    red,
                    'background of 1 has mysteriously jumped to the end color.'
                );
                Assert.areNotEqual(
                    backgrounds[0].node.getStyle('backgroundColor'),
                    backgrounds[0].bg,
                    'background of 0 has not changed at all.'
                );
                Assert.areNotEqual(
                    backgrounds[1].node.getStyle('backgroundColor'),
                    backgrounds[1].bg,
                    'background of 1 has not changed at all.'
                );
            }, 500
        );
    }
    }));

Y.lazr.testing.Runner.add(suite);
Y.lazr.testing.Runner.run();

});
