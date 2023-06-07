#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Module implementing rules to be used in ReMakeFile."""

import os
import subprocess

from remake import Builder

NAMED_RULES = []
PATTERN_RULES = []


def clearRules():
    """Clears all previously registered rules."""
    global NAMED_RULES, PATTERN_RULES

    NAMED_RULES = []
    PATTERN_RULES = []


def getRules():
    """Returns all rules."""
    return NAMED_RULES, PATTERN_RULES


class Rule():
    """Generic rule class."""
    _deps = None
    _target = None
    _action = None

    def __init__(self, target, deps, builder):
        if isinstance(deps, list):
            self._deps = deps
        elif isinstance(deps, str):
            self._deps = [deps]
        else:
            raise NotImplementedError

        self._target = target
        self._action = builder.parseAction(self._deps, self._target)
        self._register()

    def _register(self):
        global NAMED_RULES
        NAMED_RULES += [self]

    def apply(self):
        """Applies rule's action."""
        if os.path.isfile(self._target):
            return

        for dep in self._deps:
            if not os.path.isfile(dep):
                raise FileNotFoundError(f"Dependency {dep} does not exists to make {self._target}")

        try:
            self._action(self._deps, self._target)
        except TypeError:
            subprocess.run(
                " ".join(self._action),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        if not os.path.isfile(self._target):
            raise FileNotFoundError(f"Target {self._target} not created by rule `{self.actionName}`")

    @property
    def action(self):
        """Return rule's action."""
        if isinstance(self._action, list):
            return " ".join(self._action)

        return f"{self._action}({self._deps}, {self._target})"

    @property
    def actionName(self):
        """Return rule's action's description."""
        if isinstance(self._action, list):
            return " ".join(self._action)

        if self._action.__doc__ is not None:
            return self._action.__doc__

        return f"{self._action}({self._deps}, {self._target})"

    @property
    def target(self):
        """Return rule's target."""
        return self._target

    @property
    def deps(self):
        """Return rule's dependencies."""
        return self._deps


class PatternRule(Rule):
    """Pattern rule class (e.g., %.pdf:%.tex)."""
    def __init__(self, target, deps, builder):
        assert target.startswith("%")
        if isinstance(deps, list):
            for dep in deps:
                assert dep.startswith("%")
        elif isinstance(deps, str):
            assert deps.startswith("%")
        else:
            raise NotImplementedError
        super().__init__(target, deps, builder)

    def _register(self):
        global PATTERN_RULES
        PATTERN_RULES += [self]

    def expand(self, target):
        """Expands pattern rule into named rule according to target's basename
        (e.g., `pdflatex %.tex` into `pdflatex main.tex`)."""
        # Recomputing basename to obtain deps.
        basename = target.replace(self._target.replace("%", ""), "")
        assert target == self._target.replace("%", basename)

        # Computing deps and action string
        deps = [dep.replace("%", basename) for dep in self._deps]
        if isinstance(self._action, list):
            action = " ".join(self._action).replace("%", basename)
        else:
            raise NotImplementedError

        # Return instancieted rule.
        return Rule(target=target, deps=deps, builder=Builder(action=action))
