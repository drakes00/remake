#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main functions of ReMake."""

import argparse
import os
import pathlib
import re
import shutil
import sys
import json

from collections import deque
from itertools import chain
from rich.progress import Progress
from rich.console import Console
from typeguard import typechecked
from typing import Dict, List, Tuple, Union

from remake.context import addContext, popContext, addOldContext, getCurrentContext, getContexts, Context
from remake.context import isDryRun, isDevTest, isClean, setVerbose, setDryRun, setClean
from remake.paths import VirtualTarget, VirtualDep, TYP_PATH_LOOSE
from remake.rules import TYP_DEP_LIST, TYP_DEP_GRAPH, PatternRule

from remake.builders import Builder  # Import needed to avoid imports in ReMakeFile
from remake.rules import Rule  # Import needed to avoid imports in ReMakeFile


@typechecked
class AddTarget:
    """Class registering files as remake targets."""
    def __init__(self, targets: list[str | pathlib.Path] | str | pathlib.Path):
        if isinstance(targets, (str, pathlib.Path)):
            getCurrentContext().addTargets(pathlib.Path(targets).absolute())
        elif isinstance(targets, list):
            getCurrentContext().addTargets([pathlib.Path(_).absolute() for _ in targets])


@typechecked
def AddVirtualTarget(name: str) -> VirtualTarget:
    """Method registering remake targets that are not files."""
    ret = VirtualTarget(name)
    getCurrentContext().addTargets(ret)
    return ret


@typechecked
class SubReMakeDir:
    """Instantiate a sub context for a call to a sub ReMakeFile."""
    def __init__(self, subDir: str):
        executeReMakeFileFromDirectory(subDir)


@typechecked
def executeReMakeFileFromDirectory(
    cwd: str,
    configFile: str = "ReMakeFile",
    targets: list[TYP_PATH_LOOSE] | None = None
) -> Context:
    """Loads ReMakeFile from current directory in a new context and builds associated targets."""
    absCwd = os.path.abspath(cwd)
    addContext(absCwd)
    oldCwd = os.getcwd()
    os.chdir(absCwd)

    loadScript(configFile)
    deps = generateDependencyList(targets)
    executedRules = []
    if isClean() and deps:
        # We are in clean mode and there are deps to clean.
        cleanDeps(deps, configFile)
    elif not isClean() and deps:
        # We are in build mode and there are deps to build.
        executedRules = buildDeps(deps, configFile)

    os.chdir(oldCwd)
    oldContext = popContext()
    oldContext.deps = deps
    oldContext.executedRules = executedRules
    if isDevTest():
        addOldContext(absCwd, oldContext)
    return oldContext


@typechecked
def loadScript(configFile: str = "ReMakeFile") -> None:
    """Loads and execs the ReMakeFile script."""
    with open(configFile, "r", encoding="utf-8") as handle:
        script = handle.read()

    exec(script)


@typechecked
def generateDependencyList(targets: list[TYP_PATH_LOOSE] | None = None) -> TYP_DEP_LIST:
    """Generates and sorts dependency list."""
    deps = []
    if targets is None:
        targets = getCurrentContext().targets

    for target in targets:
        deps += [findBuildPath(target)]

    deps = sortDeps(deps)
    deps = optimizeDeps(deps)
    return deps


@typechecked
def findBuildPath(target: TYP_PATH_LOOSE) -> TYP_DEP_GRAPH:
    """Constructs dependency graph from registered rules."""
    depNames = []
    foundRule = None

    # Iterate over all contexts from the current context (leaf) to the parents (root).
    for context in reversed(getContexts()):
        # For each context, look for matching rules.
        namedRules, patternRules = context.rules
        matchedTarget = None
        # First with named rules that will directly match the target.
        for rule in namedRules:
            matchedTarget = rule.match(target)
            if matchedTarget:
                # Target found in rule's target.
                depNames += rule.deps
                foundRule = rule
                break

        # Stopping here as named rule was found.
        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            return {
                (matchedTarget,
                 foundRule): depNames
            }

        foundRule = None
        # Then with pattern rules that are generic.
        for rule in patternRules:
            matchedTarget, depNames = rule.match(target)
            if depNames:
                # Since rule was an anonymous rule (with *),
                # Expanding the rule to generate deps file names within match method.
                foundRule = rule
                break

        # Stopping here as pattern rule was found.
        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            return {
                (matchedTarget,
                 foundRule): depNames
            }

    # At this point, no rule was found for the target.
    if os.path.exists(str(target)):
        # And target already exists.
        if isClean():
            # We are attempting to clean an existing target no linked to any rule.
            # We thus found a ground dependency that we really don't want to erase.
            return {
                (target,
                 None): []
            }
        elif isDryRun():
            # If we are in dry run mode, just assume it's OK.
            return {
                (target,
                 None): []
            }
        else:
            # If the file exists while in build mode, then job is done.
            return {
                (target,
                 None): []
            }

    else:
        if isClean():
            # We are attempting to clean a file that does not exist and not linked to any rule.
            # This is not supposed to happen.
            raise ValueError
        elif isDryRun():
            # If we are in dry run mode, deps might not exist, just assume it's OK.
            ret = VirtualDep(target) if isinstance(target, str) else target
            return {
                (ret,
                 None): []
            }
        elif isinstance(target, (VirtualTarget, VirtualDep)):
            # Target is virtual and is not supposed to be a file, just assume it's OK.
            return {
                (target,
                 None): []
            }
        else:
            # However, if in build mode, no rule was found to make target!
            Console().print(f"[[bold red]STOP[/]] No rule to make {target}")
            sys.exit(1)


@typechecked
def sortDeps(deps: List[TYP_DEP_GRAPH]) -> TYP_DEP_LIST:
    """Sorts dependency graph as a reverse level order list.
    Snippet from: https://www.geeksforgeeks.org/reverse-level-order-traversal/"""
    tmpQueue = deque()
    ret = deque()

    # Start with last dep.
    for dep in deps[::-1]:
        tmpQueue.append(dep)

        while tmpQueue:
            node = tmpQueue.popleft()
            key, values = list(node.items())[0]
            path, rule = key

            # Make each dependencies a list
            ret.appendleft(([path], rule))

            # And iterate for sub=dependencies
            for ruleDep in values:
                tmpQueue.append(ruleDep)

    return list(ret)


@typechecked
def optimizeDeps(deps: TYP_DEP_LIST) -> TYP_DEP_LIST:
    """Removes rules from dependencies list """
    def _mergeTargetsSameRule(origDeps: TYP_DEP_LIST) -> TYP_DEP_LIST:
        """Remove duplicate calls to a rule that produces multiple dependencies, except for PatternRules to be expanded for each target."""
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

            if target[1] is not None and not isinstance(target[1], PatternRule):
                # If target is a tuple, there is a rule associated that is not a PatternRule.
                # Find all other targets that share the same rule.
                otherTargets = list(filter(lambda _: _[1] == target[1], lhsDeps))
                if otherTargets:
                    # If there are other targets, merge them.
                    allTargetsSameRule = list(chain.from_iterable([_[0] for _ in otherTargets])) + target[0]
                    allTargetsSameRule = list(
                        i for (n,
                               i) in enumerate(allTargetsSameRule) if i not in allTargetsSameRule[:n]
                    )
                    ret += [(allTargetsSameRule, target[1])]
                    for otherTarget in otherTargets:
                        deps.remove(otherTarget)
                else:
                    ret += [target]
            else:
                ret += [target]

            del deps[-1]

        ret = ret[::-1]  # And sort back the list to the correct order since we iterated from the end to the beginning.
        return ret

    def _removeDuplicatesWithNoRules(deps: TYP_DEP_LIST) -> TYP_DEP_LIST:
        """Remove duplicate targets that have no associated rule."""
        ret = []
        if len(deps) < 2:
            return deps

        for i in range(1, len(deps)):
            # Iterates over the dependencies starting from the end to compare with left side of the array.
            # First element is omitted since there is nothing to the left.
            target = deps[-i]
            lhsDeps = deps[:-i]

            # Check if target appears multiple times in the list of dependencies (including if associated with a rule).
            if target not in lhsDeps and target not in [_[0] for _ in lhsDeps if isinstance(_, tuple)]:
                ret += [target]

        ret = ret + [deps[0]]  # Put back the first target that was omitted above.
        ret = ret[::-1]  # And sort back the list to the correct order since we iterated from the end to the beginning.
        return ret

    deps = _removeDuplicatesWithNoRules(deps)
    deps = _mergeTargetsSameRule(deps)
    return deps


@typechecked
def cleanDeps(deps: TYP_DEP_LIST, configFile: str = "ReMakeFile") -> TYP_DEP_LIST:
    """Builds files marked as targets from their dependencies."""
    def _cleanDep(target):
        if os.path.exists(target):
            progress.console.print(
                f"[{job+1}/{len(deps)}] [[bold plum1]CLEAN[/bold plum1]] Cleaning dependency {target}."
            )
            if target.is_file():
                os.remove(target)
            elif target.is_dir():
                shutil.rmtree(target)

    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing {configFile} for folder {getCurrentContext().cwd}.[/bold green]"
        )
        task = progress.add_task("ReMakeFile steps", total=len(deps))
        for job, dep in enumerate(deps):
            target, rule = dep
            if rule is None:
                # Ground dependency (tree leaf).
                # Let's not delete a ground dependency.
                progress.advance(task)
            else:
                targets, rule = dep
                if isinstance(rule, PatternRule):
                    rule = rule.expand(dep[0])

                for target in targets:
                    _cleanDep(target)
                progress.advance(task)

    return deps


@typechecked
def buildDeps(deps: TYP_DEP_LIST, configFile: str = "ReMakeFile") -> TYP_DEP_LIST:
    """Builds files marked as targets from their dependencies."""
    rulesApplied = []
    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing {configFile} for folder {getCurrentContext().cwd}.[/bold green]"
        )
        task = progress.add_task("ReMakeFile steps", total=len(deps))
        for job, dep in enumerate(deps):
            targets, rule = dep
            if rule is None:
                # Ground dependency (tree leaf).
                for target in targets:
                    if isDryRun():
                        progress.console.print(
                            f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {target}"
                        )
                    elif isinstance(target, pathlib.Path) and os.path.exists(target):
                        progress.console.print(
                            f"[{job+1}/{len(deps)}] [[bold plum1]SKIP[/bold plum1]] Dependency {target} already exists."
                        )
                    elif isinstance(target, (VirtualTarget, VirtualDep)):
                        progress.console.print(
                            f"[{job+1}/{len(deps)}] [[bold plum1]SKIP[/bold plum1]] Virtual dependency: {target}"
                        )
                    else:
                        progress.console.print(
                            f"[[red bold]FAILED[/red bold]] Unable to find build path for [light_slate_blue]{target}[/light_slate_blue]! Aborting!"
                        )
                        raise FileNotFoundError
            else:
                # Dependency with a rule, need to apply the rule.
                rulesSuccess = []
                for target in targets:
                    if isinstance(rule, PatternRule):
                        rule = rule.expand(target)

                    if isDryRun():
                        progress.console.print(
                            f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {target} built with rule: {rule.actionName}"
                        )
                    else:
                        progress.console.print(f"[{job+1}/{len(deps)}] {rule.actionName}")
                        res = rule.apply(progress)
                        rulesSuccess += [res]

                # Keep track of the rules applied for return.
                if isDryRun() or (rulesSuccess and all(rulesSuccess)):
                    rulesApplied += [(targets, rule)]
            progress.advance(task)

    return rulesApplied


def main():
    """Main function of ReMake."""
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
