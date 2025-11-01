#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rule handling classes for ReMake.

This module defines the core `Rule` and `PatternRule` classes used in the ReMake
build system. These classes encapsulate the logic for defining how targets are
built from dependencies using specific builders.

Key components include:
- `Rule`: Represents a direct mapping from a set of dependencies to a set of targets,
          executed by a `Builder`.
- `PatternRule`: Extends `Rule` to handle patterns (e.g., `%.o:%.c`), allowing
                 for flexible and reusable build definitions.
"""

import os
import pathlib
import re
import subprocess
from remake.paths import TYP_DEP, TYP_PATH, TYP_PATH_LOOSE, TYP_TARGET

from rich.progress import Progress
from rich.console import Console
from typeguard import typechecked
from typing import Dict, List, Tuple, Union

from remake.context import getCurrentContext
from remake.context import isDryRun
from remake.builders import Builder
from remake.paths import VirtualTarget, VirtualDep, GlobPattern, shouldRebuild


@typechecked()
class Rule():
    """
    Represents a build rule in ReMake, defining how one or more targets are
    created from one or more dependencies using a specific builder.

    Attributes:
        _deps (list[TYP_DEP]): A list of dependencies for this rule.
        _targets (list[TYP_TARGET]): A list of targets produced by this rule.
        _builder (Builder): The builder responsible for executing the rule's action.
        _kwargs (dict): Additional keyword arguments passed to the builder's action.
    """
    _deps = []
    _targets = []
    _builder = None
    _kwargs = None

    def __init__(
        self,
        targets: list[TYP_TARGET] | TYP_TARGET,
        builder: Builder,
        deps: list[TYP_DEP] | TYP_DEP | None = None,
        ephemeral: bool = False,
        **kwargs
    ):
        """
        Initializes a Rule instance.

        Args:
            targets: A single target or a list of targets produced by the rule.
                     Can be a string, pathlib.Path, or VirtualTarget.
            builder: The Builder instance that defines the action to execute.
            deps: A single dependency or a list of dependencies required by the rule.
                  Can be a string, pathlib.Path, or VirtualDep. Defaults to None.
            ephemeral: If True, the rule is not registered in the current context.
                       Defaults to False.
            **kwargs: Additional keyword arguments to pass to the builder's action.
        """
        if deps is None:
            self._deps = []
        else:
            self._deps = self._parseDeps(deps)
        self._targets = self._parseTargets(targets)

        self._builder = builder
        self._kwargs = kwargs
        if not ephemeral:
            self._register()

    def _parseDeps(self, deps: list[TYP_DEP] | TYP_DEP):
        """
        Parses and expands dependencies to absolute paths or keeps them as VirtualDep.

        Args:
            deps: A single dependency or a list of dependencies.

        Returns:
            A list of parsed dependencies (pathlib.Path or VirtualDep).

        Raises:
            TypeError: If an unsupported dependency type is provided.
        """
        if isinstance(deps, (str, pathlib.Path)):
            # Dep is a single string or pathlib path, need to be expanded to absolute path.
            return [self._expandToAbsPath(deps)]

        if isinstance(deps, VirtualDep):
            # Dep is a single virtual dep, no need to expand.
            return [deps]

        ret = []
        if isinstance(deps, list):
            # Dep is a list, iterate over elements
            for dep in deps:
                if isinstance(dep, (str, pathlib.Path)):
                    ret += [self._expandToAbsPath(dep)]
                elif isinstance(dep, VirtualDep):
                    ret += [dep]
                else:
                    raise TypeError
        else:
            raise TypeError

        return ret

    def _parseTargets(self, targets: list[TYP_TARGET] | TYP_TARGET):
        """
        Parses and expands targets to absolute paths or keeps them as VirtualTarget.

        Args:
            targets: A single target or a list of targets.

        Returns:
            A list of parsed targets (pathlib.Path or VirtualTarget).

        Raises:
            TypeError: If an unsupported target type is provided.
        """
        if isinstance(targets, (str, pathlib.Path)):
            # Target is a single string or pathlib path, need to be expanded to absolute path.
            return [self._expandToAbsPath(targets)]

        if isinstance(targets, VirtualTarget):
            # Target is a single virtual target, no need to expand.
            return [targets]

        ret = []
        if isinstance(targets, list):
            # Target is a list, iterate over elements
            for target in targets:
                if isinstance(target, (str, pathlib.Path)):
                    ret += [self._expandToAbsPath(target)]
                elif isinstance(target, VirtualTarget):
                    ret += [target]
                else:
                    raise TypeError
        else:
            raise TypeError

        return ret

    def _register(self) -> None:
        """Registers the rule with the current ReMake context."""
        getCurrentContext().addNamedRule(self)

    def _expandToAbsPath(self, filename: str | pathlib.Path) -> pathlib.Path:
        """
        Expands a dependency or target filename to an absolute path.

        Args:
            filename: The filename to expand.

        Returns:
            A pathlib.Path object representing the absolute path.
        """
        return pathlib.Path(filename).absolute()

    def __eq__(self, other) -> bool:
        """
        Compares two Rule instances for equality.

        Rules are considered equal if their targets, dependencies, builder,
        and action are all identical.
        """
        return other is not None and isinstance(
            other,
            Rule
        ) and (self._targets,
               self._deps,
               self._builder,
               self.action) == (other._targets,
                                other._deps,
                                other._builder,
                                other.action)

    def __hash__(self):
        """Computes the hash of a Rule instance."""
        return hash(tuple([tuple(self._targets), *self._deps, self._builder]))

    def apply(self, console: Console | Progress | None = None) -> bool:
        """
        Applies the rule's action to build its targets from its dependencies.

        This method first checks if the targets need rebuilding. If so, it
        ensures dependencies exist (unless in dry-run mode) and then executes
        the builder's action. Finally, it verifies that targets were
        appropriately created or destroyed based on the builder's nature.

        Args:
            console: An optional Rich Console or Progress object for output.

        Returns:
            True if the action was applied (i.e., targets were rebuilt), False otherwise.

        Raises:
            FileNotFoundError: If a dependency does not exist or a target was
                               not created/destroyed as expected.
        """

        # Check if rule is already applied (all targets are already made).
        if self._builder.shouldRebuild:
            # Either with custom shouldRebuild method.
            if all(not self._builder.shouldRebuild(target, self._deps) for target in self._targets):
                return False
        else:
            # Or using default one.
            if all(not shouldRebuild(target, self._deps) for target in self._targets):
                return False

        # If we are not in dry run mode, ensure dependencies were made before the rule is applied.
        if not isDryRun():
            for dep in self._deps:
                if not isinstance(dep, VirtualDep) and not (os.path.isfile(dep) or os.path.isdir(dep)):
                    raise FileNotFoundError(f"Dependency {dep} does not exists to make {self._targets}")

        # Apply the rule.
        if self._builder.type == list:
            subprocess.run(
                " ".join(self.action),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        else:
            self._builder.action(self._deps, self._targets, console, **self._kwargs)

        # If we are not in dry run mode,
        if not isDryRun():
            if self._builder.isDestructive:
                # If builder is destructive, ensure targets are properly destroyed.
                for target in self._targets:
                    if not isinstance(target, VirtualTarget) and (os.path.isfile(target) or os.path.isdir(target)):
                        raise FileNotFoundError(f"Target {target} not destroyed by rule `{self.actionName}`")
            else:
                # If builder is creative, ensure targets were made after the rule is applied.
                for target in self._targets:
                    if not isinstance(target, VirtualTarget) and not (os.path.isfile(target) or os.path.isdir(target)):
                        raise FileNotFoundError(f"Target {target} not created by rule `{self.actionName}`")

        return True

    def match(self, other: TYP_PATH_LOOSE) -> TYP_PATH | None:
        """
        Checks if the rule's targets match a given path.

        Args:
            other: The path to match against the rule's targets.
                   Can be a string, pathlib.Path, VirtualTarget, or VirtualDep.

        Returns:
            The matching target (as TYP_PATH) if a match is found, otherwise None.
        """
        for target in self._targets:
            # Important to compare strings because targets can be of multiple type (str, pathlib.Path, virtual).
            if re.fullmatch(str(target), str(other)):
                return target
        return None

    @property
    def action(self) -> list[str] | tuple[str, list[str], list[str]]:
        """
        Returns the rule's action, with automatic variables expanded.

        The action can be a list of strings (for shell commands) or a tuple
        representing a callable action with its dependencies and targets.
        """
        action = self._builder.parseAction(self._deps, self._targets)

        def _handleListTypes(elems):
            ret = []
            for elem in elems:
                if isinstance(elem, pathlib.Path):
                    ret += [str(elem)]
                elif isinstance(elem, GlobPattern):
                    ret += [elem]  # Specifically keep GlobPattern as is to be expanded later.
                else:
                    ret += [str(elem)]
            return ret

        if isinstance(action, list):
            return _handleListTypes(action)

        deps = _handleListTypes(self._deps)
        targets = _handleListTypes(self._targets)
        return (str(self._builder.action), deps, targets)

    @property
    def actionName(self) -> str:
        """
        Returns a human-readable description of the rule's action.

        For shell commands, it returns the joined command string.
        For callable actions, it returns a formatted string including the
        callable's name and its dependencies/targets.
        """
        action = self.action
        if isinstance(action, list):
            return " ".join(action)

        if isinstance(action, tuple):
            return rf"{action[0]}(\[{', '.join(action[1])}], \[{', '.join(action[2])}])"

        raise NotImplementedError

    @property
    def targets(self) -> list[VirtualTarget | pathlib.Path | GlobPattern]:
        """Returns the list of targets for this rule."""
        return self._targets

    @property
    def deps(self) -> list[VirtualDep | pathlib.Path | GlobPattern]:
        """Returns the list of dependencies for this rule."""
        return self._deps


@typechecked()
class PatternRule(Rule):
    """
    Represents a pattern-based build rule in ReMake (e.g., `%.o:%.c`).

    Pattern rules allow defining generic build instructions that can be applied
    to multiple files matching a specific pattern. They are instantiated into
    concrete `Rule` objects when a matching target is requested.

    Attributes:
        _exclude (list[str]): A list of patterns to exclude from this rule.
    """
    _exclude = []

    def __init__(self, target: str, deps: list[str] | str, builder: Builder, exclude: list[str] | None = None):
        """
        Initializes a PatternRule instance.

        Args:
            target: The target pattern (e.g., "*.pdf"). Must contain exactly one '*'.
            deps: A single dependency pattern or a list of dependency patterns (e.g., "*.tex").
                  Each pattern must contain exactly one '*'.
            builder: The Builder instance that defines the action to execute.
            exclude: An optional list of patterns to exclude from this rule. Defaults to None.

        Raises:
            AssertionError: If target or dependency patterns do not contain exactly one '*'.
            NotImplementedError: If an unsupported dependency type is provided.
        """
        # FIXME Does not seem to handle PatternRules such as "a*.foo"
        assert target.count("*") == 1
        if isinstance(deps, list):
            for dep in deps:
                assert dep.count("*") == 1
        elif isinstance(deps, str):
            assert deps.count("*") == 1
        else:
            raise NotImplementedError
        self._exclude = [] if exclude is None else exclude
        super().__init__(targets=target, deps=deps, builder=builder)

    def _register(self) -> None:
        """Registers the pattern rule with the current ReMake context."""
        getCurrentContext().addPatternRule(self)

    def _expandToAbsPath(self, filename: str) -> GlobPattern:
        """
        Overrides the base Rule's method to return a GlobPattern for pattern rules.

        Pattern rules are not expanded to absolute paths at this stage; instead,
        their patterns are encapsulated in `GlobPattern` objects.

        Args:
            filename: The pattern string.

        Returns:
            A GlobPattern object.
        """
        return GlobPattern(filename)

    @property
    def targetPattern(self) -> str:
        """Returns the glob pattern associated with the target of this rule."""
        return self._targets[0].pattern

    def instanciate(self, other: pathlib.Path, dep: GlobPattern) -> pathlib.Path:
        """
        Instantiates a dependency path based on a matching target and a dependency pattern.

        This method calculates the "raddix" (the part of the filename that matches '*')
        from the `other` path and the `targetPattern`, and then applies it to the
        `dep` pattern to generate a concrete dependency path.

        Args:
            other: The concrete target path that matched the `targetPattern`.
            dep: The `GlobPattern` representing the dependency.

        Returns:
            A `pathlib.Path` object representing the instantiated dependency.
        """
        prefix, suffix = self.targetPattern.split("*")
        raddix = str(other).replace(prefix, "").replace(suffix, "")
        return pathlib.Path(dep.pattern.replace("*", raddix))

    def match(self, other: pathlib.Path | str) -> tuple[pathlib.Path, list[pathlib.Path]]:
        """
        Checks if a given path matches the pattern rule's target pattern and is not excluded.

        If a match is found, it returns the matching target path and a list of
        instantiated dependency paths.

        Args:
            other: The path to check against the pattern rule's target pattern.

        Returns:
            A tuple containing:
            - The matching target path (as pathlib.Path).
            - A list of instantiated dependency paths (as pathlib.Path).
            If no match or if excluded, returns (pathlib.Path(other), []).
        """
        if isinstance(other, str):
            other = pathlib.Path(other)

        # Check if other is excluded from pattern rule.
        if str(other) in self._exclude:
            return (pathlib.Path(other), [])

        ret = []
        assert all(isinstance(_, GlobPattern) for _ in self._targets)
        if other.match(self.targetPattern):
            for dep in self._deps:
                ret += [self.instanciate(other, dep)]

        return (pathlib.Path(other), ret)

    def expand(self, target: pathlib.Path) -> Rule:
        """
        Expands the pattern rule into a concrete `Rule` instance for a specific target.

        This method takes a concrete target path that matches the pattern rule's
        target pattern and generates a new `Rule` object with specific dependencies
        and an action tailored to that target.

        Args:
            target: The concrete target path (e.g., `main.pdf`).

        Returns:
            A new `Rule` instance representing the expanded rule.

        Raises:
            AssertionError: If the provided target does not match the rule's target pattern.
        """
        assert target.match(self.targetPattern)

        # Computing deps and action string
        # TODO Would be nice to remember target and deps position in builder's action and replace them at the latest.
        deps = [target.with_suffix(dep.suffix) for dep in self._deps]
        if isinstance(self.action, list):
            action = []
            for elem in self.action:
                if isinstance(elem, GlobPattern):
                    action += [str(super()._expandToAbsPath(target.with_suffix(elem.suffix)))]
                else:
                    action += [elem]
            action = " ".join(action)
        else:
            action = self.action

        # Return instancieted rule.
        return Rule(targets=target, deps=deps, builder=Builder(action=action, ephemeral=True), ephemeral=True)

    @property
    def allTargets(self) -> list[pathlib.Path]:
        """
        Returns a list of all possible concrete targets that can be generated by this pattern rule.

        This is achieved by globbing for possible dependencies and then deriving
        the corresponding target paths.
        """
        allDeps = []
        for dep in self._deps:
            allDeps += list(pathlib.Path(".").rglob(dep.pattern))

        suffix = self.targetPattern.replace("*", "")
        return [pathlib.Path(dep).with_suffix(suffix) for dep in allDeps]


# Type alias for a list of dependencies, where each dependency is a tuple
# containing a list of paths and an optional Rule.
TYP_DEP_LIST = list[tuple[list[TYP_PATH], Rule | None]]
# Type alias for a dependency graph, represented as a dictionary mapping
# (path, Rule | None) tuples to lists of TYP_DEP_GRAPH.
TYP_DEP_GRAPH = dict[tuple[TYP_PATH, Rule | None], list["TYP_DEP_GRAPH"]]
