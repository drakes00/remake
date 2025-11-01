#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ReMake functions and classes for managing execution contexts and global state.

This module provides mechanisms for handling the global state of the ReMake
build system, including verbose mode, dry-run mode, clean mode, and development
test mode. It also defines the `Context` class, which encapsulates the state
(builders, rules, targets) for a specific build directory, and functions for
managing a stack of these contexts.
"""

from collections import deque
from typeguard import typechecked

VERBOSE = False
DRY_RUN = False
DEV_TEST = False
CLEAN = False
REBUILD = False


@typechecked()
def isVerbose() -> bool:
    """
    Checks if ReMake is currently running in verbose mode.

    Returns:
        True if verbose mode is active, False otherwise.
    """
    return VERBOSE


@typechecked()
def isDryRun() -> bool:
    """
    Checks if ReMake is currently running in dry-run mode.

    In dry-run mode, actions are announced but not actually executed.

    Returns:
        True if dry-run mode is active, False otherwise.
    """
    return DRY_RUN


@typechecked()
def isDevTest() -> bool:
    """
    Checks if ReMake is currently running in development test mode.

    Development test mode enables additional features for debugging and testing.

    Returns:
        True if development test mode is active, False otherwise.
    """
    return DEV_TEST


@typechecked()
def isClean() -> bool:
    """
    Checks if ReMake is currently running in clean mode.

    In clean mode, ReMake attempts to remove generated targets.

    Returns:
        True if clean mode is active, False otherwise.
    """
    return CLEAN


@typechecked()
def isRebuild() -> bool:
    """
    Checks if ReMake is currently running in rebuild mode.

    In rebuild mode, ReMake attempts to clean then build targets.

    Returns:
        True if rebuild mode is active, False otherwise.
    """
    return REBUILD


@typechecked()
def setDryRun() -> None:
    """Sets the global state to dry-run mode."""
    global DRY_RUN
    DRY_RUN = True


@typechecked()
def setVerbose() -> None:
    """Sets the global state to verbose mode."""
    global VERBOSE
    VERBOSE = True


@typechecked()
def setDevTest() -> None:
    """Sets the global state to development test mode."""
    global DEV_TEST
    DEV_TEST = True


@typechecked()
def setClean() -> None:
    """Sets the global state to clean mode."""
    global CLEAN
    CLEAN = True


@typechecked()
def setRebuild() -> None:
    """Sets the global state to rebuild mode."""
    global REBUILD
    REBUILD = True


@typechecked()
def unsetDryRun() -> None:
    """Unsets the global dry-run mode."""
    global DRY_RUN
    DRY_RUN = False


@typechecked()
def unsetVerbose() -> None:
    """Unsets the global verbose mode."""
    global VERBOSE
    VERBOSE = False


@typechecked()
def unsetDevTest() -> None:
    """
    Unsets the global development test mode and resets old contexts.
    """
    global DEV_TEST
    DEV_TEST = False
    resetOldContexts()


@typechecked()
def unsetClean() -> None:
    """Unsets the global clean mode."""
    global CLEAN
    CLEAN = False


@typechecked()
def unsetRebuild() -> None:
    """Unsets the global rebuild mode."""
    global REBUILD
    REBUILD = False


def getOldContext(cwd):
    """
    Retrieves a previously stored context for a given working directory.

    This function is primarily for development and testing purposes.

    Args:
        cwd (str): The current working directory associated with the context.

    Returns:
        Context: The old context object if found.
    """
    return DEV_OLD_CONTEXTS[cwd]


def addOldContext(cwd, context):
    """
    Adds a context to a dictionary of old contexts for later inspection.

    This function is primarily for development and testing purposes.

    Args:
        cwd (str): The current working directory associated with the context.
        context (Context): The context object to store.
    """
    DEV_OLD_CONTEXTS[cwd] = context


def resetOldContexts():
    """Empties the dictionary of stored old contexts."""
    global DEV_OLD_CONTEXTS
    DEV_OLD_CONTEXTS = {}


def getCurrentContext():
    """
    Returns the current active `Context` from the top of the context stack.

    Returns:
        Context: The current context object.
    """
    return CONTEXTS[-1]


def getContexts():
    """
    Returns a list of all contexts currently in the stack, ordered from oldest to newest.

    Returns:
        list[Context]: A list of context objects.
    """
    return CONTEXTS


def addContext(cwd):
    """
    Pushes a new `Context` onto the context stack, effectively starting a new build scope.

    Args:
        cwd (str): The current working directory for the new context.
    """
    CONTEXTS.append(Context(cwd))


def popContext():
    """
    Removes and returns the current `Context` from the top of the context stack,
    ending the current build scope.

    Returns:
        Context: The context object that was removed.
    """
    return CONTEXTS.pop()


class Context():
    """
    Represents an execution context for ReMake, encapsulating all information
    relevant to a specific build scope (e.g., a ReMakeFile in a directory).

    Each context maintains its own set of builders, rules, targets, and
    dependencies. This allows for hierarchical and modular build structures.

    Attributes:
        _cwd (str): The current working directory associated with this context.
        _builders (list[Builder]): A list of builders registered within this context.
        _namedRules (list[Rule]): A list of named rules registered within this context.
        _patternRules (list[PatternRule]): A list of pattern rules registered within this context.
        _executedRules (list): A list of rules that have been executed in this context.
        _targets (list): A list of targets declared in this context.
        _deps (list): The resolved dependency graph/list for this context's targets.
    """
    _cwd = None
    _builders = None
    _namedRules = None
    _patternRules = None
    _executedRules = None
    _targets = None
    _deps = None

    def __init__(self, cwd):
        """
        Initializes a new Context instance.

        Args:
            cwd (str): The current working directory for this context.
        """
        self._cwd = cwd
        self._builders = []
        self._namedRules = []
        self._patternRules = []
        self._executedRules = []
        self._targets = []
        self._deps = None

    @property
    def cwd(self):
        """Returns the current working directory of this context."""
        return self._cwd

    def addTargets(self, targets):
        """
        Adds one or more targets to this context's list of targets.

        Duplicates are prevented.

        Args:
            targets: A single target or a list of targets to add.
        """
        if isinstance(targets, list):
            for target in targets:
                if not target in self._targets:
                    self._targets += [target]
        else:
            if not targets in self._targets:
                self._targets += [targets]

    @property
    def targets(self) -> list:
        """Returns the list of targets declared in this context."""
        return self._targets

    def clearTargets(self):
        """Clears all targets registered in this context."""
        self._targets = []

    def addNamedRule(self, rule):
        """
        Adds a named rule to this context.

        Args:
            rule (Rule): The `Rule` object to add.
        """
        self._namedRules += [rule]

    def addPatternRule(self, rule):
        """
        Adds a pattern rule to this context.

        Args:
            rule (PatternRule): The `PatternRule` object to add.
        """
        self._patternRules += [rule]

    @property
    def rules(self):
        """
        Returns a tuple containing the named rules and pattern rules of this context.

        Returns:
            tuple[list[Rule], list[PatternRule]]: A tuple (named rules, pattern rules).
        """
        return (self._namedRules, self._patternRules)

    def clearRules(self):
        """Clears all named and pattern rules registered in this context."""
        self._namedRules = []
        self._patternRules = []

    @property
    def executedRules(self):
        """Returns the list of rules that were executed within this context."""
        return self._executedRules

    @executedRules.setter
    def executedRules(self, rules):
        """
        Sets the list of executed rules for this context.

        Args:
            rules (list): A list of executed rules.
        """
        self._executedRules = rules

    def addBuilder(self, builder):
        """
        Adds a builder to this context.

        Args:
            builder (Builder): The `Builder` object to add.
        """
        self._builders += [builder]

    @property
    def builders(self):
        """Returns the list of builders registered in this context."""
        return self._builders

    def clearBuilders(self):
        """Clears all builders registered in this context."""
        self._builders = []

    @property
    def deps(self):
        """Returns the resolved dependency graph/list for this context's targets."""
        return self._deps

    @deps.setter
    def deps(self, deps):
        """
        Sets the resolved dependency graph/list for this context's targets.

        Args:
            deps (list): The dependency list.
        """
        self._deps = deps


# A deque (double-ended queue) used as a stack to manage active `Context` objects.
CONTEXTS = deque()
# The initial context, always present at the bottom of the stack.
CONTEXTS.append(Context(None))
# A dictionary used in development test mode to store old contexts for inspection.
DEV_OLD_CONTEXTS = {}
