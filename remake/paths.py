#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Path handling classes of ReMake."""

import os
import pathlib

from typeguard import typechecked


@typechecked()
class VirtualTarget():
    """Class representing remake targets that are not files."""
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return super().__repr__() + f"(name={self._name})"

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return isinstance(other, VirtualTarget) and self._name == other._name

    def __lt__(self, other):
        return self._name < other._name

    def matches(self, other):
        return self._name == other


@typechecked()
class VirtualDep():
    """Class registering remake dependencies that are not files."""
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return super().__repr__() + f"(name={self._name})"

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return isinstance(other, VirtualDep) and self._name == other._name


@typechecked()
class GlobPattern():
    """Class registering remake dependencies that are glob patterns of pattern rules (e.g., *.foo)."""
    def __init__(self, pattern: str):
        self._pattern = pattern

    def __str__(self):
        return self._pattern

    def __hash__(self):
        return hash(self._pattern)

    def __eq__(self, other):
        return isinstance(other, GlobPattern) and self._pattern == other._pattern

    @property
    def pattern(self) -> str:
        """Returns the pattern associated."""
        return self._pattern

    @property
    def suffix(self):
        """Returns the suffix of the pattern associated."""
        # '*' is expected to be first character by PatternRule.__init__
        return self._pattern[1:]


@typechecked()
def shouldRebuild(target: VirtualTarget | pathlib.Path, deps: list[VirtualDep | pathlib.Path]):
    """Returns True if target should be built, False else.
    Target is built is not existing or if any dependency is more recent."""
    if isinstance(target, VirtualTarget):
        # Target is virtual, always rebuild.
        return True

    if not os.path.exists(target):
        # If target does not already exists.
        return True

    # Target exists, check for newer deps.
    for dep in deps:
        if isinstance(dep, VirtualDep):
            # Dependency is virtual, nothing to compare to, skip to next dep.
            continue
        if os.path.getctime(dep) > os.path.getctime(target):
            # Dep was created after target, thus more recent, thus should rebuild.
            return True

    # All deps are older than target, no need for rebuild.
    return False


TYP_TARGET = pathlib.Path | VirtualTarget | str
TYP_DEP = pathlib.Path | VirtualDep | str
TYP_PATH = pathlib.Path | VirtualTarget | VirtualDep
TYP_PATH_LOOSE = TYP_PATH | str
