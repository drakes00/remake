#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main funtions of ReMake."""

import argparse
import glob
import os
import pathlib
import re
import subprocess
import sys

from collections import deque
from rich.progress import Progress
from rich.console import Console

from remake.context import addContext, popContext, addOldContext, getCurrentContext, getContexts, resetOldContexts

VERBOSE = False
DRY_RUN = False
DEV_TEST = False
CLEAN = False


def setDryRun():
    """Sets run to dry run mode."""
    global DRY_RUN
    DRY_RUN = True


def setVerbose():
    """Sets run to verbose mode."""
    global VERBOSE
    VERBOSE = True


def setDevTest():
    """Sets run to development mode."""
    global DEV_TEST
    DEV_TEST = True


def setClean():
    """Sets run to clean mode."""
    global CLEAN
    CLEAN = True


def unsetDryRun():
    """Sets run to NOT dry run mode."""
    global DRY_RUN
    DRY_RUN = False


def unsetVerbose():
    """Sets run to NOT verbose mode."""
    global VERBOSE
    VERBOSE = False


def unsetDevTest():
    """Sets run to NOT development mode."""
    global DEV_TEST
    DEV_TEST = False
    resetOldContexts()


def unsetClean():
    """Sets run to NOT clean mode."""
    global CLEAN
    CLEAN = False


class Target():
    """Class registering files as remake targets."""
    def __init__(self, targets):
        getCurrentContext().addTargets(targets)


class Builder():
    """Generic builder class."""
    _action = None

    def __init__(self, action, ephemeral=False):
        self._action = action
        if not ephemeral:
            self._register()

    def _register(self):
        getCurrentContext().addBuilder(self)

    def parseAction(self, deps, targets):
        """Parses builder action for automatic variables ($@, etc)."""
        if isinstance(self._action, str):
            ret = self._action
            if deps:
                ret = ret.replace("$<", " ".join(deps))
                ret = ret.replace("$^", deps[0])
            ret = ret.replace("$@", " ".join(targets))
            ret = ret.split(" ")
            return ret

        return self._action

    @property
    def action(self):
        """Returns builder's action."""
        return self._action


class Rule():
    """Generic rule class."""
    _deps = None
    _targets = None
    _action = None

    def __init__(self, targets, builder, deps=[], ephemeral=False):
        if isinstance(deps, list):
            self._deps = deps
        elif isinstance(deps, str):
            self._deps = [deps]
        else:
            raise NotImplementedError

        if isinstance(targets, list):
            self._targets = targets
        elif isinstance(targets, str):
            self._targets = [targets]
        else:
            raise NotImplementedError

        self._action = builder.parseAction(self._deps, self._targets)
        self._expandToAbsPath()
        if not ephemeral:
            self._register()

    def _register(self):
        getCurrentContext().addNamedRule(self)

    def _expandToAbsPath(self):
        self._deps = [os.path.abspath(dep) for dep in self._deps]
        self._targets = [os.path.abspath(target) for target in self._targets]

    def __eq__(self, other):
        return (self._targets, self._deps, self._action) == (other._targets, other._deps, other._action)

    def __hash__(self):
        try:
            # When action is a function
            return hash(tuple([tuple(self._targets), *self._deps, self._action]))
        except TypeError:
            # When action is a subprocess string list
            return hash(tuple([tuple(self._targets), *self._deps, *self._action]))

    def apply(self, console):
        """Applies rule's action."""
        if all([os.path.isfile(target) for target in self._targets]):
            return

        for dep in self._deps:
            if not DRY_RUN and not os.path.isfile(dep):
                raise FileNotFoundError(f"Dependency {dep} does not exists to make {self._target}")

        if isinstance(self._action, list):
            subprocess.run(
                " ".join(self._action),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        else:
            self._action(self._deps, self._targets, console)

        if not DRY_RUN:
            for target in self._targets:
                if not os.path.isfile(target):
                    raise FileNotFoundError(f"Target {target} not created by rule `{self.actionName}`")

    @property
    def action(self):
        """Return rule's action."""
        if isinstance(self._action, list):
            return " ".join(self._action)

        return f"{self._action}({self._deps}, {self._targets})"

    @property
    def actionName(self):
        """Return rule's action's description."""
        if isinstance(self._action, list):
            return " ".join(self._action)

        if self._action.__doc__ is not None:
            return self._action.__doc__

        return f"{self._action}({self._deps}, {self._targets})"

    @property
    def targets(self):
        """Return rule's targets."""
        return self._targets

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
        super().__init__(targets=target, deps=deps, builder=builder)

    def _register(self):
        getCurrentContext().addPatternRule(self)

    def _expandToAbsPath(self):
        pass

    def expand(self, target):
        """Expands pattern rule into named rule according to target's basename
        (e.g., `pdflatex %.tex` into `pdflatex main.tex`)."""
        # Recomputing basename to obtain deps.
        basename = target.replace(self._targets[0].replace("%", ""), "")
        assert target == self._targets[0].replace("%", basename)

        # Computing deps and action string
        deps = [dep.replace("%", basename) for dep in self._deps]
        if isinstance(self._action, list):
            action = " ".join(self._action).replace("%", basename)
        else:
            action = self._action

        # Return instancieted rule.
        return Rule(targets=target, deps=deps, builder=Builder(action=action, ephemeral=True), ephemeral=True)

    @property
    def allTargets(self):
        """Returns all possible targets from globing possible dependencies."""
        allDeps = []
        for dep in self._deps:
            starDep = dep.replace("%", "*")
            allDeps += glob.glob(f"**/{starDep}", recursive=True)

        suffix = self._targets[0].replace("%", "")
        return [pathlib.Path(dep).with_suffix(suffix) for dep in allDeps]


class SubReMakeDir():
    """Instanciate a sub context for a call to a sub ReMakeFile."""
    def __init__(self, subDir):
        executeReMakeFileFromDirectory(subDir)


def executeReMakeFileFromDirectory(cwd):
    """Loads ReMakeFile from current directory in a new context and builds
    associated targets."""
    absCwd = os.path.abspath(cwd)
    addContext(absCwd)
    oldCwd = os.getcwd()
    os.chdir(absCwd)

    loadScript()
    deps = generateDependencyList()
    if CLEAN and deps:
        # We are in clean mode and there are deps to clean.
        cleanDeps(deps)
    elif not CLEAN and deps:
        # We are in build mode and there are deps to build.
        buildDeps(deps)

    os.chdir(oldCwd)
    oldContext = popContext()
    oldContext.deps = deps
    if DEV_TEST:
        addOldContext(absCwd, oldContext)
    return oldContext


def loadScript():
    """Loads and execs the ReMakeFile script."""
    with open("ReMakeFile", "r", encoding="utf-8") as handle:
        script = handle.read()

    exec(script)


def generateDependencyList():
    """Generates and sorts dependency list."""
    deps = []
    for target in getCurrentContext().targets:
        deps += [findBuildPath(target)]

    deps = sortDeps(deps)
    deps = optimizeDeps(deps)
    return deps


def findBuildPath(target):
    """Constructs dependency graph from registered rules."""
    # First converts the target to its absolute path to not mix it up with another file.
    target = os.path.abspath(target)

    depNames = []
    foundRule = None

    # Iterate over all contexts from the current context (leaf) to the parents (root).
    for context in reversed(getContexts()):
        # For each context, look for matching rules.
        namedRules, patternRules = context.rules
        # First with named rules that will directly match the target.
        for rule in namedRules:
            for ruleTarget in rule.targets:
                occ = re.fullmatch(ruleTarget, target)
                if occ:
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
            for ruleTarget in rule.targets:
                regex = ruleTarget.replace("%", "([a-zA-Z0-9_/-]*)")
                occ = re.fullmatch(regex + "$", target)
                if occ:
                    # Since rule was an anonymous rule (with %),
                    # Expanding the rule to generate deps file names.
                    for dep in rule.deps:
                        depName = occ.expand(dep.replace("%", r"\1"))
                        depNames += [depName]

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
    if os.path.isfile(target):
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
        else:
            # However, if in build mode, no rule was found to make target!
            Console().print(f"[[bold red]STOP[/]] No rule to make {target}")
            sys.exit(1)


def sortDeps(deps):
    """Sorts dependency graph as a reverse level order list.
    Snippet from: https://www.geeksforgeeks.org/reverse-level-order-traversal/"""
    tmpQueue = deque()
    ret = deque()

    for dep in deps[::-1]:
        tmpQueue.append(dep)

        while tmpQueue:
            node = tmpQueue.popleft()
            if isinstance(node, str):
                ret.appendleft(node)
            elif isinstance(node, dict):
                ret.appendleft(list(node.keys())[0])
                for ruleDep in list(node.values())[0]:
                    tmpQueue.append(ruleDep)

    return list(ret)


def optimizeDeps(deps):
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
                        [i for n,
                         i in enumerate(allTargetsSameRule) if i not in allTargetsSameRule[:n]]
                    )

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


def cleanDeps(deps):
    """Builds files marked as targets from their dependencies."""
    def _cleanDep(target):
        if os.path.isfile(target):
            progress.console.print(
                f"[{job+1}/{len(deps)}] [[bold plum1]CLEAN[/bold plum1]] Cleaning dependency {target}."
            )
            os.remove(target)

    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing ReMakeFile for folder {getCurrentContext().cwd}.[/bold green]"
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


def buildDeps(deps):
    """Builds files marked as targets from their dependencies."""
    rulesApplied = []
    with Progress() as progress:
        progress.console.print(
            f"[+] [green bold] Executing ReMakeFile for folder {getCurrentContext().cwd}.[/bold green]"
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
                        f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {target} built with rule: {rule.action}"
                    )
                else:
                    progress.console.print(f"[{job+1}/{len(deps)}] {rule.actionName}")
                    rule.apply(progress)

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
    args = argparser.parse_args()

    # Global arguments handling.
    if args.verbose:
        setVerbose()
    if args.dry_run:
        setDryRun()
        setVerbose()

    # Cleaning handling.
    if args.clean:
        setClean()

    executeReMakeFileFromDirectory(os.getcwd())


if __name__ == "__main__":
    main()
