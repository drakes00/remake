#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Path handling classes and utility functions for ReMake.

This module defines classes to represent different types of paths and dependencies
within the ReMake build system:
- `VirtualTarget`: Represents a target that is not a physical file on the filesystem.
- `VirtualDep`: Represents a dependency that is not a physical file.
- `GlobPattern`: Represents a glob pattern used in pattern rules.

It also provides the `shouldRebuild` function to determine if a target needs to be
rebuilt based on its dependencies.
"""

import os
import pathlib

from typeguard import typechecked


@typechecked()
class VirtualTarget():
    """
    Represents a target in ReMake that does not correspond to a physical file
    on the filesystem.

    Virtual targets are used for actions that don't produce a tangible file,
    but rather represent a state or a logical grouping of other targets.

    Attributes:
        _name (str): The name of the virtual target.
    """
    def __init__(self, name: str):
        """
        Initializes a VirtualTarget instance.

        Args:
            name: The unique name of the virtual target.
        """
        self._name = name

    def __str__(self):
        """Returns the name of the virtual target."""
        return self._name

    def __repr__(self):
        """Returns a developer-friendly string representation of the VirtualTarget."""
        return super().__repr__() + f"(name={self._name})"

    def __hash__(self):
        """Computes the hash of the VirtualTarget based on its name."""
        return hash(self._name)

    def __eq__(self, other):
        """
        Compares two VirtualTarget instances for equality.

        Two VirtualTarget instances are considered equal if they are both
        VirtualTarget objects and have the same name.
        """
        return isinstance(other, (VirtualTarget, VirtualDep)) and self._name == other._name

    def __lt__(self, other):
        """
        Compares two VirtualTarget instances for less than.

        This allows for sorting of VirtualTarget objects based on their names.
        """
        return self._name < other._name

    def matches(self, other):
        """
        Checks if the virtual target's name matches another object.

        Args:
            other: The object to compare against.

        Returns:
            True if the virtual target's name is equal to the other object, False otherwise.
        """
        return self._name == other


@typechecked()
class VirtualDep():
    """
    Represents a dependency in ReMake that does not correspond to a physical file
    on the filesystem.

    Virtual dependencies are used for abstract dependencies that don't have a
    physical representation but are necessary for a rule to execute.

    Attributes:
        _name (str): The name of the virtual dependency.
    """
    def __init__(self, name: str):
        """
        Initializes a VirtualDep instance.

        Args:
            name: The unique name of the virtual dependency.
        """
        self._name = name

    def __str__(self):
        """Returns the name of the virtual dependency."""
        return self._name

    def __repr__(self):
        """Returns a developer-friendly string representation of the VirtualDep."""
        return super().__repr__() + f"(name={self._name})"

    def __hash__(self):
        """Computes the hash of the VirtualDep based on its name."""
        return hash(self._name)

    def __eq__(self, other):
        """
        Compares two VirtualDep instances for equality.

        Two VirtualDep instances are considered equal if they are both
        VirtualDep objects and have the same name.
        """
        return isinstance(other, (VirtualTarget, VirtualDep)) and self._name == other._name


@typechecked()
class GlobPattern():
    """
    Represents a glob pattern used in pattern rules within ReMake.

    This class encapsulates a glob pattern (e.g., "*.foo") which is typically
    used to match multiple files as dependencies or targets in a rule.

    Attributes:
        _pattern (str): The glob pattern string.
    """
    def __init__(self, pattern: str):
        """
        Initializes a GlobPattern instance.

        Args:
            pattern: The glob pattern string (e.g., "*.c", "src/*.h").
        """
        self._pattern = pattern

    def __str__(self):
        """Returns the glob pattern string."""
        return self._pattern

    def __hash__(self):
        """Computes the hash of the GlobPattern based on its pattern string."""
        return hash(self._pattern)

    def __eq__(self, other):
        """
        Compares two GlobPattern instances for equality.

        Two GlobPattern instances are considered equal if they are both
        GlobPattern objects and have the same pattern string.
        """
        return isinstance(other, GlobPattern) and self._pattern == other._pattern

    @property
    def pattern(self) -> str:
        """Returns the glob pattern string."""
        return self._pattern

    @property
    def suffix(self):
        """
        Returns the suffix part of the glob pattern.

        Assumes the pattern starts with '*' (e.g., "*.foo" -> ".foo").
        """
        # '*' is expected to be first character by PatternRule.__init__
        return self._pattern[1:]


@typechecked()
def shouldRebuild(target: VirtualTarget | pathlib.Path, deps: list[VirtualDep | pathlib.Path]):
    """
    Determines whether a given target needs to be rebuilt.

    A target needs to be rebuilt if:
    1. It is a `VirtualTarget` (always rebuilt).
    2. It does not exist on the filesystem.
    3. Any of its physical dependencies are newer than the target.

    Args:
        target: The target, which can be a `VirtualTarget` or a `pathlib.Path`.
        deps: A list of dependencies, which can be `VirtualDep` or `pathlib.Path` objects.

    Returns:
        True if the target should be rebuilt, False otherwise.
    """
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


# Type alias for a target, which can be a physical path, a virtual target, or a string.
TYP_TARGET = pathlib.Path | VirtualTarget | str
# Type alias for a dependency, which can be a physical path, a virtual dependency, or a string.
TYP_DEP = pathlib.Path | VirtualDep | str
# Type alias for any path-like object (physical path, virtual target, or virtual dependency).
TYP_PATH = pathlib.Path | VirtualTarget | VirtualDep
# Type alias for a loose path-like object, including strings.
TYP_PATH_LOOSE = TYP_PATH | str
