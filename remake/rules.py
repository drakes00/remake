#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rule handling classes of ReMake."""

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
    """Generic rule class."""
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
        getCurrentContext().addNamedRule(self)

    def _expandToAbsPath(self, filename: str | pathlib.Path) -> pathlib.Path:
        """Expands dep or target to absolute path."""
        return pathlib.Path(filename).absolute()

    def __eq__(self, other) -> bool:
        return other is not None and isinstance(other,
                                                Rule) and (self._targets,
                                                           self._deps,
                                                           self._builder,
                                                           self.action
                                                          ) == (other._targets,
                                                                other._deps,
                                                                other._builder,
                                                                other.action)

    def __hash__(self):
        return hash(tuple([tuple(self._targets), *self._deps, self._builder]))

    def apply(self, console: Console | Progress | None = None) -> bool:
        """Applies rule's action.
        Returns True if action was applied, False else.
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
        """Returns True if other matches any target of the rule, False else."""
        for target in self._targets:
            # Important to compare strings because targets can be of multiple type (str, pathlib.Path, virtual).
            if re.fullmatch(str(target), str(other)):
                return target
        return None

    @property
    def action(self) -> list[str] | tuple[str, list[str], list[str]]:
        """Return rule's action."""
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
        """Return rule's action's description."""
        action = self.action
        if isinstance(action, list):
            return " ".join(action)

        if isinstance(action, tuple):
            return rf"{action[0]}(\[{', '.join(action[1])}], \[{', '.join(action[2])}])"

        raise NotImplementedError

    @property
    def targets(self) -> list[VirtualTarget | pathlib.Path | GlobPattern]:
        """Return rule's targets."""
        return self._targets

    @property
    def deps(self) -> list[VirtualDep | pathlib.Path | GlobPattern]:
        """Return rule's dependencies."""
        return self._deps


@typechecked()
class PatternRule(Rule):
    """Pattern rule class (e.g., *.pdf:*.tex)."""
    _exclude = []

    def __init__(self, target: str, deps: list[str] | str, builder: Builder, exclude: list[str] | None = None):
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
        getCurrentContext().addPatternRule(self)

    def _expandToAbsPath(self, filename: str) -> GlobPattern:
        """PatternRules are not expanded!"""
        return GlobPattern(filename)

    @property
    def targetPattern(self) -> str:
        """Returns pattern associated to the target."""
        return self._targets[0].pattern

    def instanciate(self, other: pathlib.Path, dep: GlobPattern) -> pathlib.Path:
        """Returns the pattern of the target instanciated with the raddix of `other`."""
        prefix, suffix = self.targetPattern.split("*")
        raddix = str(other).replace(prefix, "").replace(suffix, "")
        return pathlib.Path(dep.pattern.replace("*", raddix))

    def match(self, other: pathlib.Path | str) -> tuple[pathlib.Path, list[pathlib.Path]]:
        """Check if `other` matches dependency pattern and is not in exclude list.
        If True, returns corresponding dependencies names.
        Else, returns []."""
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
        """Expands pattern rule into named rule according to target's basename
        (e.g., `pdflatex *.tex` into `pdflatex main.tex`)."""
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
        """Returns all possible targets from globing possible dependencies."""
        allDeps = []
        for dep in self._deps:
            allDeps += list(pathlib.Path(".").rglob(dep.pattern))

        suffix = self.targetPattern.replace("*", "")
        return [pathlib.Path(dep).with_suffix(suffix) for dep in allDeps]


#TYP_DEP_LIST = list[TYP_PATH | tuple[Union[TYP_PATH, List[TYP_PATH]], Rule]]
TYP_DEP_LIST = list[tuple[list[TYP_PATH], Rule | None]]
TYP_DEP_GRAPH = dict[tuple[TYP_PATH, Rule | None], list["TYP_DEP_GRAPH"]]
