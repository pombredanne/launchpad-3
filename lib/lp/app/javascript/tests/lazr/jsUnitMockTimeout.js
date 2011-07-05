/*
    Version: MPL 1.1/GPL 2.0/LGPL 2.1

    The contents of this file are subject to the Mozilla Public License Version
    1.1 (the "License"); you may not use this file except in compliance with
    the License. You may obtain a copy of the License at
    http://www.mozilla.org/MPL/

    Software distributed under the License is distributed on an "AS IS" basis,
    WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
    for the specific language governing rights and limitations under the
    License.

    The Original Code is Edward Hieatt code.

    The Initial Developer of the Original Code is
    Edward Hieatt, edward@jsunit.net.
    Portions created by the Initial Developer are Copyright (C) 2003
    the Initial Developer. All Rights Reserved.

    Author Edward Hieatt, edward@jsunit.net

    Alternatively, the contents of this file may be used under the terms of
    either the GNU General Public License Version 2 or later (the "GPL"), or
    the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
    in which case the provisions of the GPL or the LGPL are applicable instead
    of those above. If you wish to allow use of your version of this file only
    under the terms of either the GPL or the LGPL, and not to allow others to
    use your version of this file under the terms of the MPL, indicate your
    decision by deleting the provisions above and replace them with the notice
    and other provisions required by the LGPL or the GPL. If you do not delete
    the provisions above, a recipient may use your version of this file under
    the terms of any one of the MPL, the GPL or the LGPL.
*/

// Mock setTimeout, clearTimeout
// Contributed by Pivotal Computer Systems, www.pivotalsf.com
//
// Copied from the JsUnit 2.2alpha1 release, made in Mar 24 2006
// (http://www.jsunit.net/)

var Clock = {
    timeoutsMade: 0,
    scheduledFunctions: {},
    nowMillis: 0,
    reset: function() {
        this.scheduledFunctions = {};
        this.nowMillis = 0;
        this.timeoutsMade = 0;
    },
    tick: function(millis) {
        var oldMillis = this.nowMillis;
        var newMillis = oldMillis + millis;
        this.runFunctionsWithinRange(oldMillis, newMillis);
        this.nowMillis = newMillis;
    },
    runFunctionsWithinRange: function(oldMillis, nowMillis) {
        var scheduledFunc;
        var funcsToRun = [];
        for (var timeoutKey in this.scheduledFunctions) {
            scheduledFunc = this.scheduledFunctions[timeoutKey];
            if (scheduledFunc != undefined &&
                scheduledFunc.runAtMillis >= oldMillis &&
                scheduledFunc.runAtMillis <= nowMillis) {
                funcsToRun.push(scheduledFunc);
                this.scheduledFunctions[timeoutKey] = undefined;
            }
        }

        if (funcsToRun.length > 0) {
            funcsToRun.sort(function(a, b) {
                return a.runAtMillis - b.runAtMillis;
            });
            for (var i = 0; i < funcsToRun.length; ++i) {
                try {
                    this.nowMillis = funcsToRun[i].runAtMillis;
                    funcsToRun[i].funcToCall();
                    if (funcsToRun[i].recurring) {
                        Clock.scheduleFunction(funcsToRun[i].timeoutKey,
                                funcsToRun[i].funcToCall,
                                funcsToRun[i].millis,
                                true);
                    }
                } catch(e) {
                    console.log(e);
                }
            }
            this.runFunctionsWithinRange(oldMillis, nowMillis);
        }
    },
    scheduleFunction: function(timeoutKey, funcToCall, millis, recurring) {
        Clock.scheduledFunctions[timeoutKey] = {
            runAtMillis: Clock.nowMillis + millis,
            funcToCall: funcToCall,
            recurring: recurring,
            timeoutKey: timeoutKey,
            millis: millis
        };
    }
};

function setTimeout(funcToCall, millis) {
    Clock.timeoutsMade = Clock.timeoutsMade + 1;
    Clock.scheduleFunction(Clock.timeoutsMade, funcToCall, millis, false);
    return Clock.timeoutsMade;
}

function setInterval(funcToCall, millis) {
    Clock.timeoutsMade = Clock.timeoutsMade + 1;
    Clock.scheduleFunction(Clock.timeoutsMade, funcToCall, millis, true);
    return Clock.timeoutsMade;
}

function clearTimeout(timeoutKey) {
    Clock.scheduledFunctions[timeoutKey] = undefined;
}

function clearInterval(timeoutKey) {
    Clock.scheduledFunctions[timeoutKey] = undefined;
}
