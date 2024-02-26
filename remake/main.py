#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main funtions of ReMake."""

import argparse
from collections.abc import Callable
import glob
import os
import pathlib
import re
import subprocess
import sys

from typeguard import typechecked

from collections import deque
from rich.progress import Progress
from rich.console import Console

from remake.context import addContext, popContext, addOldContext, getCurrentContext, getContexts, resetOldContexts, Context

VERBOSE = False
DRY_RUN = False
DEV_TEST = False
CLEAN = False


@typechecked()
def setDryRun() -> None:
    """Sets run to dry run mode."""
    global DRY_RUN
    DRY_RUN = True


@typechecked()
def setVerbose() -> None:
    """Sets run to verbose mode."""
    global VERBOSE
    VERBOSE = True


@typechecked()
def setDevTest() -> None:
    """Sets run to development mode."""
    global DEV_TEST
    DEV_TEST = True


@typechecked()
def setClean() -> None:
    """Sets run to clean mode."""
    global CLEAN
    CLEAN = True


@typechecked()
def unsetDryRun() -> None:
    """Sets run to NOT dry run mode."""
    global DRY_RUN
    DRY_RUN = False


@typechecked()
def unsetVerbose() -> None:
    """Sets run to NOT verbose mode."""
    global VERBOSE
    VERBOSE = False


@typechecked()
def unsetDevTest() -> None:
    """Sets run to NOT development mode."""
    global DEV_TEST
    DEV_TEST = False
    resetOldContexts()


@typechecked()
def unsetClean() -> None:
    """Sets run to NOT clean mode."""
    global CLEAN
    CLEAN = False


@typechecked()
class AddTarget():
    """Class registering files as remake targets."""
    def __init__(self, targets: list[str | pathlib.Path] | str | pathlib.Path):
        if isinstance(targets, (str, pathlib.Path)):
            getCurrentContext().addTargets(pathlib.Path(targets).absolute())
        elif isinstance(targets, list):
            getCurrentContext().addTargets([pathlib.Path(_).absolute() for _ in targets])


@typechecked()
class VirtualTarget():
    """Class representing remake targets that are not files."""
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return isinstance(other, VirtualTarget) and self._name == other._name

    def __lt__(self, other):
        return self._name < other._name


@typechecked()
class AddVirtualTarget(VirtualTarget):
    """Class registering remake targets that are not files."""
    def __init__(self, name: str):
        super().__init__(name)
        getCurrentContext().addTargets(self)


@typechecked()
class VirtualDep():
    """Class registering remake dependencies that are not files."""
    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name

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
        return self._pattern

    @property
    def suffix(self):
        # '*' is expected to be first character by PatternRule.__init__
        return self._pattern[1:]


@typechecked()
def shouldRebuild(target: VirtualTarget | pathlib.Path, deps: list[VirtualDep | pathlib.Path]):
    """Returns True if target should be built, False else.
    Target is built is not existing or if any dependency is more recent."""
    if isinstance(target, VirtualTarget):
        # Target is virtual, always rebuild.
        return True
    if not os.path.isfile(target):
        # If target does not already exists.
        return True
    else:
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


@typechecked()
class Builder():
    """Generic builder class."""
    _action = None

    def __init__(
        self,
        action: list[str] | str | Callable[[list[str],
                                            list[str],
                                            Console],
                                           None],
        ephemeral: bool = False
    ):
        if isinstance(action, str):
            self._action = action.split(" ")
        else:
            self._action = action
        if not ephemeral:
            self._register()

    def __eq__(self, other):
        return self._action == other._action

    def __hash__(self):
        if isinstance(self._action, list):
            return hash(tuple(self._action))  # Hash based on list action
        else:
            return hash(id(self._action))  # Hash based on function

    def _register(self) -> None:
        getCurrentContext().addBuilder(self)

    def parseAction(
        self,
        deps: list[VirtualDep | pathlib.Path | GlobPattern],
        targets: list[VirtualTarget | pathlib.Path | GlobPattern]
    ) -> list[str] | Callable[[list[str],
                               list[str],
                               Console],
                              None]:
        """Parses builder action for automatic variables ($@, etc)."""
        def _replace_in_action(llist, pattern, repl):
            try:
                i = llist.index(pattern)
            except ValueError:
                return llist
            return llist[:i] + repl + llist[i + 1:]

        if isinstance(self._action, list):
            ret = self._action
            ret = _replace_in_action(ret, "$@", targets)
            if deps:
                ret = _replace_in_action(ret, "$^", [deps[0]])
                ret = _replace_in_action(ret, "$<", deps)
            return ret

        return self._action

    @property
    def action(self) -> Callable[[list[str], list[str], Console], None]:
        """Returns builder's action."""
        return self._action

    @property
    def type(self):
        """Returns build's action's type (list vs. callable)."""
        return type(self._action)


@typechecked()
class Rule():
    """Generic rule class."""
    _deps = []
    _targets = []
    _builder = None
    _kwargs = None

    def __init__(
        self,
        targets: list[VirtualTarget | str | pathlib.Path] | VirtualTarget | str | pathlib.Path,
        builder: Builder,
        deps: list[VirtualDep | str | pathlib.Path] | VirtualDep | str | pathlib.Path = [],
        ephemeral: bool = False,
        **kwargs
    ):
        self._deps = self._parseDeps(deps)
        self._targets = self._parseTargets(targets)

        self._builder = builder
        self._kwargs = kwargs
        if not ephemeral:
            self._register()

    def _parseDeps(self, deps: list[VirtualDep | str | pathlib.Path] | VirtualDep | str | pathlib.Path):
        if isinstance(deps, (str, pathlib.Path)):
            # Dep is a single string or pathlib path, need to be expanded to absolute path.
            return [self._expandToAbsPath(deps)]
        elif isinstance(deps, VirtualDep):
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

    def _parseTargets(self, targets: list[VirtualTarget | str | pathlib.Path] | VirtualTarget | str | pathlib.Path):
        if isinstance(targets, (str, pathlib.Path)):
            # Target is a single string or pathlib path, need to be expanded to absolute path.
            return [self._expandToAbsPath(targets)]
        elif isinstance(targets, VirtualTarget):
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
        return pathlib.Path(filename).resolve()

    def __eq__(self, other) -> bool:
        return (self._targets, self._deps, self._builder) == (other._targets, other._deps, other._builder)

    def __hash__(self):
        return hash(tuple([tuple(self._targets), *self._deps, self._builder]))

    def apply(self, console: Console | Progress | None) -> bool:
        """Applies rule's action.
        Returns True if action was applied, False else.
        """

        # Check if rule is already applied (all targets are already made).
        if all(not shouldRebuild(target, self._deps) for target in self._targets):
            return False

        # If we are not in dry run mode, ensure dependencies were made before the rule is applied.
        if not DRY_RUN:
            for dep in self._deps:
                if not isinstance(dep, VirtualDep) and not os.path.isfile(dep):
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

        # If we are not in dry run mode, ensure targets were made after the rule is applied.
        if not DRY_RUN:
            for target in self._targets:
                if not isinstance(target, VirtualTarget) and not os.path.isfile(target):
                    raise FileNotFoundError(f"Target {target} not created by rule `{self.actionName}`")

        return True

    @property
    def action(self) -> list[str]:
        """Return rule's action."""
        action = self._builder.parseAction(self._deps, self._targets)
        if isinstance(action, list):
            ret = []
            for elem in action:
                if isinstance(elem, pathlib.Path):
                    ret += [str(elem)]
                elif isinstance(elem, GlobPattern):
                    ret += [elem.pattern]
                else:
                    ret += [elem]
            return ret

        return [f"{action}({self._deps}, {self._targets})"]

    @property
    def actionName(self) -> str:
        """Return rule's action's description."""
        action = self.action
        if isinstance(action, list):
            return " ".join(action)

        if action.__doc__ is not None:
            return action.__doc__

        return f"{action}({self._deps}, {self._targets})"

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

    def __init__(self, target: str, deps: list[str] | str, builder: Builder, exclude: list[str] = []):
        # FIXME Does not seem to handle PatternRules such as "a*.foo"
        assert target.startswith("*")
        if isinstance(deps, list):
            for dep in deps:
                assert dep.startswith("*")
        elif isinstance(deps, str):
            assert deps.startswith("*")
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
        return self._targets[0].pattern

    def match(self, other: pathlib.Path | str) -> list[pathlib.Path]:
        """Check if `other` matches dependency pattern and is not in exclude list.
        If True, returns corresponding dependencies names.
        Else, returns []."""
        if isinstance(other, str):
            other = pathlib.Path(other)

        # Check if other is excluded from pattern rule.
        if str(other) in self._exclude:
            return []

        ret = []
        assert all(isinstance(_, GlobPattern) for _ in self._targets)
        if other.match(self.targetPattern):
            for dep in self._deps:
                ret += [other.with_suffix(dep.suffix)]

        return ret

    def expand(self, target: pathlib.Path) -> Rule:
        """Expands pattern rule into named rule according to target's basename
        (e.g., `pdflatex *.tex` into `pdflatex main.tex`)."""
        assert target.match(self.targetPattern)

        # Computing deps and action string
        # TODO Would be nice to remember target and deps position in builder's acition and replace them at the latest.
        deps = [target.with_suffix(dep.suffix) for dep in self._deps]
        if isinstance(self.action, list):
            action = []
            for elem in self.action:
                if isinstance(elem, GlobPattern):
                    action += [str(target.with_suffix(elem.suffix))]
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


@typechecked()
class SubReMakeDir():
    """Instanciate a sub context for a call to a sub ReMakeFile."""
    def __init__(self, subDir):
        executeReMakeFileFromDirectory(subDir)


@typechecked()
def executeReMakeFileFromDirectory(cwd: str, configFile: str = "ReMakeFile", targets: list | None = None) -> Context:
    """Loads ReMakeFile from current directory in a new context and builds
    associated targets."""
    absCwd = os.path.abspath(cwd)
    addContext(absCwd)
    oldCwd = os.getcwd()
    os.chdir(absCwd)

    loadScript(configFile)
    deps = generateDependencyList(targets)
    executedRules = []
    if CLEAN and deps:
        # We are in clean mode and there are deps to clean.
        cleanDeps(deps, configFile)
    elif not CLEAN and deps:
        # We are in build mode and there are deps to build.
        executedRules = buildDeps(deps, configFile)

    os.chdir(oldCwd)
    oldContext = popContext()
    oldContext.deps = deps
    oldContext.executedRules = executedRules
    if DEV_TEST:
        addOldContext(absCwd, oldContext)
    return oldContext


@typechecked()
def loadScript(configFile: str = "ReMakeFile") -> None:
    """Loads and execs the ReMakeFile script."""
    with open(configFile, "r", encoding="utf-8") as handle:
        script = handle.read()

    exec(script)


@typechecked()
def generateDependencyList(
    targets: list | None = None
) -> list[pathlib.Path | tuple[pathlib.Path | tuple[pathlib.Path,
                                                    ...],
                               Rule]] | tuple[pathlib.Path | tuple[pathlib.Path,
                                                                   ...],
                                              Rule]:
    """Generates and sorts dependency list."""
    deps = []
    if targets is None:
        targets = getCurrentContext().targets

    for target in targets:
        deps += [findBuildPath(target)]

    deps = sortDeps(deps)
    deps = optimizeDeps(deps)
    return deps


@typechecked()
def findBuildPath(
    target: pathlib.Path | VirtualTarget | VirtualDep
) -> VirtualTarget | VirtualDep | pathlib.Path | dict:
    """Constructs dependency graph from registered rules."""
    depNames = []
    foundRule = None

    # import pdb
    # pdb.set_trace()

    # Iterate over all contexts from the current context (leaf) to the parents (root).
    for context in reversed(getContexts()):
        # For each context, look for matching rules.
        namedRules, patternRules = context.rules
        # First with named rules that will directly match the target.
        for rule in namedRules:
            for ruleTarget in rule.targets:
                # Important to compare strings because targets can be of multiple type (str, pathlib.Path, virtual).
                if re.fullmatch(str(ruleTarget), str(target)):
                    # Target found in rule's target.
                    depNames += rule.deps
                    foundRule = rule
                    break

        # Stopping here as named rule was found.
        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            depNames = [ii for n, ii in enumerate(depNames) if ii not in depNames[:n]]
            return {
                (target,
                 foundRule): depNames
            }

        foundRule = None
        # Then with pattern rules that are generic.
        for rule in patternRules:
            depNames = rule.match(str(target))
            if depNames:
                # Since rule was an anonymous rule (with *),
                # Expanding the rule to generate deps file names within match method.
                foundRule = rule
                break

        # Stopping here as pattern rule was found.
        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            depNames = [ii for n, ii in enumerate(depNames) if ii not in depNames[:n]]
            return {
                (target,
                 foundRule): depNames
            }

    # At this point, no rule was found for the target.
    if os.path.isfile(str(target)):
        # And target already exists.
        if CLEAN:
            # We are attempting to clean an existing target no linked to any rule.
            # We thus found a ground dependency that we really don't want to erase.
            return target
        elif DRY_RUN:
            # If we are in dry run mode, just assume it's OK.
            return target
        else:
            # If the file exists while in build mode, then job is done.
            return target

    else:
        if CLEAN:
            # We are attempting to clean a file that does not exist and not linked to any rule.
            # This is not supposed to happen.
            raise ValueError
        elif DRY_RUN:
            # If we are in dev mode, deps might not exit, just assume it's OK.
            return target
        elif isinstance(target, (VirtualTarget, VirtualDep)):
            # Target is virtual and is not supposed to be a file, just assume it's OK.
            return target
        else:
            # However, if in build mode, no rule was found to make target!
            Console().print(f"[[bold red]STOP[/]] No rule to make {target}")
            sys.exit(1)


@typechecked()
def sortDeps(
    deps: list[VirtualTarget | VirtualDep | pathlib.Path | dict]
) -> list[pathlib.Path | tuple[pathlib.Path | tuple[pathlib.Path,
                                                    ...],
                               Rule]]:
    """Sorts dependency graph as a reverse level order list.
    Snippet from: https://www.geeksforgeeks.org/reverse-level-order-traversal/"""
    tmpQueue = deque()
    ret = deque()

    for dep in deps[::-1]:
        tmpQueue.append(dep)

        while tmpQueue:
            node = tmpQueue.popleft()
            if isinstance(node, pathlib.Path):
                ret.appendleft(node)
            elif isinstance(node, dict):
                ret.appendleft(list(node.keys())[0])
                for ruleDep in list(node.values())[0]:
                    tmpQueue.append(ruleDep)

    return list(ret)


@typechecked()
def optimizeDeps(
    deps: list[pathlib.Path | tuple[pathlib.Path | tuple[pathlib.Path,
                                                         ...],
                                    Rule]]
) -> list[pathlib.Path | tuple[pathlib.Path | tuple[pathlib.Path,
                                                    ...],
                               Rule]]:
    """Removes rules from dependencies list """
    def _mergeTargetsSameRule(origDeps):
        """Remove duplicate calls to a rule that produces multiple dependencies."""
        ret = []
        if len(origDeps) < 2:
            return origDeps

        # We will remove items from deps as we process the list so let's make a copy first.
        deps = origDeps.copy()

        # Keep going as long a there are deps still not processed.
        while len(deps) > 0:
            # Iterates over the dependencies starting from the end to compare with left side of the array.
            # First element is omitted since their is nothing to the left.
            target = deps[-1]
            lhsDeps = deps[:-1]

            if isinstance(target, tuple):
                # If target is a tuple, there is a rule associated.
                # Find all other targets that share the same rule.
                otherTargets = list(filter(lambda _: isinstance(_, tuple) and _[1] == target[1], lhsDeps))
                if otherTargets:
                    # If there are other targets, merge them.
                    allTargetsSameRule = [_[0] for _ in otherTargets] + [target[0]]
                    allTargetsSameRule = tuple(
                        i for (n,
                               i) in enumerate(allTargetsSameRule) if i not in allTargetsSameRule[:n]
                    )
                    allTargetsSameRule = allTargetsSameRule[0] if len(allTargetsSameRule) == 1 else allTargetsSameRule
                    ret += [(allTargetsSameRule, target[1])]
                    for otherTarget in otherTargets:
                        deps.remove(otherTarget)
                else:
                    ret += [target]
            else:
                ret += [target]
            del deps[-1]

        ret = ret[::-1]  # And sort back the list to the correct order since we iterated from the end to the begening.
        return ret

    def _removeDuplicatesWithNoRules(deps):
        """Remove duplicate targets that have no associated rule."""
        ret = []
        if len(deps) < 2:
            return deps

        for i in range(1, len(deps)):
            # Iterates over the dependencies starting from the end to compare with left side of the array.
            # First element is omitted since their is nothing to the left.
            target = deps[-i]
            lhsDeps = deps[:-i]

            # Check if target appears multiple times in the list of dependencies (including if associated with a rule.
            if target not in lhsDeps and target not in [_[0] for _ in lhsDeps if isinstance(_, tuple)]:
                ret += [target]

        ret = ret + [deps[0]]  # Put back the first target that was omitted above.
        ret = ret[::-1]  # And sort back the list to the correct order since we iterated from the end to the begening.
        return ret

    deps = _mergeTargetsSameRule(deps)
    deps = _removeDuplicatesWithNoRules(deps)
    return deps


@typechecked()
def cleanDeps(deps: list[pathlib.Path | tuple[pathlib.Path,
                                              Rule]],
              configFile: str = "ReMakeFile") -> list[tuple[pathlib.Path,
                                                            Rule]]:
    """Builds files marked as targets from their dependencies."""
    def _cleanDep(target):
        if os.path.isfile(target):
            progress.console.print(
                f"[{job+1}/{len(deps)}] [[bold plum1]CLEAN[/bold plum1]] Cleaning dependency {target}."
            )
            os.remove(target)

    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing {configFile} for folder {getCurrentContext().cwd}.[/bold green]"
        )
        task = progress.add_task("ReMakeFile steps", total=len(deps))
        for job, dep in enumerate(deps):
            if isinstance(dep, str):
                # Ground dependency (tree leaf).
                # Let's not delete a ground dependency..
                progress.advance(task)
            elif isinstance(dep, tuple):
                target, rule = dep
                if isinstance(rule, PatternRule):
                    rule = rule.expand(dep[0])

                if isinstance(target, tuple):
                    for tmp in target:
                        _cleanDep(tmp)
                else:
                    _cleanDep(target)
                progress.advance(task)

    return deps


@typechecked()
def buildDeps(deps: list[pathlib.Path | tuple[pathlib.Path,
                                              Rule]],
              configFile: str = "ReMakeFile") -> list[tuple[pathlib.Path | tuple[pathlib.Path,
                                                                                 pathlib.Path],
                                                            Rule]]:
    """Builds files marked as targets from their dependencies."""
    rulesApplied = []
    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing {configFile} for folder {getCurrentContext().cwd}.[/bold green]"
        )
        task = progress.add_task("ReMakeFile steps", total=len(deps))
        for job, dep in enumerate(deps):
            if isinstance(dep, str):
                # Ground dependency (tree leaf).
                if DRY_RUN is True:
                    progress.console.print(
                        f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {dep}"
                    )
                elif os.path.isfile(dep):
                    progress.console.print(
                        f"[{job+1}/{len(deps)}] [[bold plum1]SKIP[/bold plum1]] Dependency {dep} already exists."
                    )
                else:
                    progress.console.print(
                        f"[[red bold]FAILED[/red bold]] Unable to find build path for [light_slate_blue]{dep}[/light_slate_blue]! Aborting!"
                    )
                    raise FileNotFoundError
                progress.advance(task)
            elif isinstance(dep, tuple):
                # Dependency with a rule, need to apply the rule.
                target, rule = dep
                if isinstance(rule, PatternRule):
                    rule = rule.expand(dep[0])

                if DRY_RUN:
                    progress.console.print(
                        f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {target} built with rule: {rule.actionName}"
                    )
                    # Keep track of the rules applied for return.
                    rulesApplied += [(target, rule)]
                else:
                    progress.console.print(f"[{job+1}/{len(deps)}] {rule.actionName}")
                    if rule.apply(progress):
                        # Keep track of the rules applied for return.
                        rulesApplied += [(target, rule)]

                progress.advance(task)

    return rulesApplied


def main():
    """Main funtion of ReMake."""
    argparser = argparse.ArgumentParser(prog="remake", description="ReMake is a make-like tool.")
    argparser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
    )
    argparser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
    )
    argparser.add_argument(
        "-c",
        "--clean",
        action="store_true",
    )
    argparser.add_argument(
        "-f",
        "--config-file",
        type=str,
        default="ReMakeFile",
    )
    argparser.add_argument(
        "targets",
        type=str,
        nargs='*',
        default=argparse.SUPPRESS,
    )
    args = argparser.parse_intermixed_args()

    # Global arguments handling.
    if args.verbose:
        setVerbose()
    if args.dry_run:
        setDryRun()
        setVerbose()

    # Cleaning handling.
    if args.clean:
        setClean()

    # Handling target.
    if "targets" not in args:
        args.targets = None

    executeReMakeFileFromDirectory(os.getcwd(), configFile=args.config_file, targets=args.targets)


if __name__ == "__main__":
    main()
