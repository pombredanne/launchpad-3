/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Things that YUI3 really needs.
 *
 * @module lp
 * @submodule extras-dict
 */

YUI.add('lp.extras-dict', function(Y) {

Y.log('loading lp.extras-dict');

var namespace = Y.namespace("lp.extras"),
    owns = Y.Object.owns;

/**
 * An object type that resembles Python's dict.
 *
 * This is *experimental*. It may be useful to have a dict-like type
 * in JavaScript, hence this, but it may turn out to be a distraction,
 * hence why it's in a separate module.
 */
var Dict;

Dict = function(initial) {
    if (initial !== undefined) {
        this.update(initial);
    }
};

// Static members.
Y.mix(Dict, {

    fromKeys: function(keys, def) {
        var dict = new Dict();
        Y.Array.each(keys, function(key) { dict[key] = def; });
        return dict;
    }

}, true);

// Prototype members.
Y.mix(Dict.prototype, {

    clear: function() {
        var del = function(key) { delete this[key]; };
        this.keys().forEach(del, this);
    },

    copy: function() {
        return new Dict(this);
    },

    get: function(key, def) {
        return owns(this, key) ? this[key] : def;
    },

    hasKey: function(key) {
        return owns(this, key);
    },

    items: function() {
        return this.keys().map(function(key) {
            return {key: key, value: this[key]};
        }, this);
    },

    keys: function() {
        return Y.Object.keys(this);
    },

    pop:  function() {
        var key, value;
        for (key in this) {
            if (owns(this, key)) {
                value = this[key];
                delete this[key];
                return value;
            }
        }
        return undefined;
    },

    popItem: function() {
        var key, value;
        for (key in this) {
            if (owns(this, key)) {
                value = this[key];
                delete this[key];
                return {key: key, value: value};
            }
        }
        return undefined;
    },

    setDefault: function(key, def) {
        if (owns(this, key)) {
            return this[key];
        }
        else {
            this[key] = def;
            return def;
        }
    },

    update: function(source) {
        var key;
        for (key in source) {
            if (owns(source, key)) {
                this[key] = source[key];
            }
        }
    },

    values: function() {
        return Y.Object.values(this);
    },

    isEmpty: function() {
        return Y.Object.isEmpty(this);
    },

    isSame: function(other) {
        var key, keys = Y.Object.keys(this),
            other_key, other_keys = Y.Object.keys(other);
        if (keys.length !== other_keys.length) {
            return false;
        }
        keys.sort(); other_keys.sort();
        while (keys.length > 0) {
            key = keys.pop(); other_key = other_keys.pop();
            if (key !== other_key || this[key] !== other[key]) {
                return false;
            }
        }
        return true;
    }

}, true);

// Exports.
namespace.Dict = Dict;

}, "0.1", {requires: ["yui-base"]});
