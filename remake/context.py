#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ReMake functions to handle contexts."""

from collections import deque


def getOldContext(cwd):
    """Dev purpose: returns an old context for inspection."""
    return DEV_OLD_CONTEXTS[cwd]


def addOldContext(cwd, context):
    """Dev purpose: adds an old context for inspection."""
    DEV_OLD_CONTEXTS[cwd] = context


def resetOldContexts():
    """Empties old contexts."""
    global DEV_OLD_CONTEXTS
    DEV_OLD_CONTEXTS = {}


def getCurrentContext():
    """Returns current context."""
    return CONTEXTS[-1]


def getContexts():
    """Returns all paths from contexts."""
    return CONTEXTS


def addContext(cwd):
    """Adds a path to contexts."""
    CONTEXTS.append(Context(cwd))


def popContext():
    """Pops lats path from contexts."""
    return CONTEXTS.pop()


class Context():
    """Class registering a context of execution (builders, rules, targets)."""
    _cwd = None
    _builders = None
    _namedRules = None
    _patternRules = None
    _targets = None
    _deps = None

    def __init__(self, cwd):
        self._cwd = cwd
        self._builders = []
        self._namedRules = []
        self._patternRules = []
        self._targets = []
        self._deps = None

    @property
    def cwd(self):
        """Returns the CWD from current context."""
        return self._cwd

    def addTargets(self, targets):
        """Adds targets to current context."""
        if isinstance(targets, list):
            self._targets += targets
        else:
            self._targets += [targets]

    @property
    def targets(self):
        """Returns the list of targets to build from current context."""
        return self._targets

    def clearTargets(self):
        """Clears list of targets of current context."""
        self._targets = []

    def addNamedRule(self, rule):
        """Adds a named rule to current context."""
        self._namedRules += [rule]

    def addPatternRule(self, rule):
        """Adds a pattern rule to current context."""
        self._patternRules += [rule]

    @property
    def rules(self):
        """Returns the list of rules from current context."""
        return (self._namedRules, self._patternRules)

    def clearRules(self):
        """Clears list of rules of current context."""
        self._namedRules = []
        self._patternRules = []

    def addBuilder(self, builder):
        """Adds a builder to current context."""
        self._builders += [builder]

    @property
    def builders(self):
        """Returns the list of builders from current context."""
        return self._builders

    def clearBuilders(self):
        """Clears list of builders of current context."""
        self._builders = []

    @property
    def deps(self):
        """Returns dependencies to make target."""
        return self._deps

    @deps.setter
    def deps(self, deps):
        """Modifies the dependencies of the context."""
        self._deps = deps


CONTEXTS = deque()
CONTEXTS.append(Context(None))
DEV_OLD_CONTEXTS = {}
