#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main funtions of ReMake."""

import argparse
import os
import re
import subprocess

from collections import deque
from rich.progress import Progress

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
    global DEV_TEST, DEV_OLD_CONTEXTS
    DEV_TEST = False
    DEV_OLD_CONTEXTS = {}


def unsetClean():
    """Sets run to NOT clean mode."""
    global CLEAN
    CLEAN = False


def getOldContext(cwd):
    """Dev purpose: returns an old context for inspection."""
    return DEV_OLD_CONTEXTS[cwd]


def getCurrentContext():
    """Returns current context."""
    return CONTEXTS[-1]


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

    def parseAction(self, deps, target):
        """Parses builder action for automatic variables ($@, etc)."""
        if isinstance(self._action, str):
            ret = self._action
            if deps:
                ret = ret.replace("$<", " ".join(deps))
                ret = ret.replace("$^", deps[0])
            ret = ret.replace("$@", target)
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
    _target = None
    _action = None

    def __init__(self, target, deps, builder, ephemeral=False):
        if isinstance(deps, list):
            self._deps = deps
        elif isinstance(deps, str):
            self._deps = [deps]
        else:
            raise NotImplementedError

        self._target = target
        self._action = builder.parseAction(self._deps, self._target)

        self._expandToAbsPath()
        if not ephemeral:
            self._register()

    def _register(self):
        getCurrentContext().addNamedRule(self)

    def _expandToAbsPath(self):
        self._deps = [os.path.abspath(dep) for dep in self._deps]
        self._target = os.path.abspath(self._target)

    def __eq__(self, other):
        return (self._target, self._deps, self._action) == (other._target, other._deps, other._action)

    def __hash__(self):
        try:
            # When action is a function
            return hash(tuple([self._target, *self._deps, self._action]))
        except TypeError:
            # When action is a subprocess string list
            return hash(tuple([self._target, *self._deps, *self._action]))

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
        getCurrentContext().addPatternRule(self)

    def _expandToAbsPath(self):
        pass

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
            action = self._action

        # Return instancieted rule.
        return Rule(target=target, deps=deps, builder=Builder(action=action, ephemeral=True), ephemeral=True)


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


class SubReMakeDir():
    """Instanciate a sub context for a call to a sub ReMakeFile."""
    def __init__(self, subDir):
        executeReMakeFileFromDirectory(subDir)


def executeReMakeFileFromDirectory(cwd):
    """Loads ReMakeFile from current directory in a new context and builds
    associated targets."""
    absCwd = os.path.abspath(cwd)
    CONTEXTS.append(Context(absCwd))
    oldCwd = os.getcwd()
    os.chdir(absCwd)

    loadScript()
    deps = generateDependencyList()
    if CLEAN and deps:
        cleanTargets(deps)
    elif not CLEAN and deps:
        buildTargets(deps)

    os.chdir(oldCwd)
    oldContext = CONTEXTS.pop()
    oldContext.deps = deps
    if DEV_TEST:
        DEV_OLD_CONTEXTS[absCwd] = oldContext
    return oldContext


def loadScript():
    """Loads and execs the ReMakeFile script."""
    with open("ReMakeFile", "r") as handle:
        script = handle.read()

    exec(script)


def generateDependencyList():
    """Generates and sorts dependency list."""
    deps = []
    for target in getCurrentContext().targets:
        deps += [findBuildPath(target)]

    deps = sortDeps(deps)
    return deps


def findBuildPath(target):
    """Constructs dependency graph from registered rules."""
    target = os.path.abspath(target)
    if os.path.isfile(target) and not CLEAN:
        return target

    depNames = []
    foundRule = None

    # Iterate over all contexts from the current context (leaf) to the parents (root).
    for context in reversed(CONTEXTS):
        # For each context, look for matching rules.
        namedRules, patternRules = context.rules
        for rule in namedRules:
            occ = re.fullmatch(rule.target, target)
            if occ:
                # Target found in rule's target.
                depNames += rule.deps
                foundRule = rule
                break

        # Stopping here is named rule was found.
        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            depNames = [ii for n, ii in enumerate(depNames) if ii not in depNames[:n]]
            return {
                (target,
                 foundRule): depNames
            }

        foundRule = None
        for rule in patternRules:
            regex = rule.target.replace("%", "([a-zA-Z0-9_/-]*)")
            occ = re.fullmatch(regex + "$", target)
            if occ:
                # Rule was an anonymous rule (with %).
                # Expanding rule to generate deps file names.
                for dep in rule.deps:
                    depName = occ.expand(dep.replace("%", r"\1"))
                    depNames += [depName]

                foundRule = rule
                break

        if foundRule is not None:
            depNames = [findBuildPath(dep) for dep in depNames]
            depNames = [ii for n, ii in enumerate(depNames) if ii not in depNames[:n]]
            return {
                (target,
                 foundRule): depNames
            }

    return target


def sortDeps(targets):
    """Sorts dependency graph as a reverse level order list."""
    tmpQueue = deque()
    ret = deque()

    for target in targets[::-1]:
        tmpQueue.append(target)

        while tmpQueue:
            node = tmpQueue.popleft()
            if isinstance(node, str):
                ret.appendleft(node)
            elif isinstance(node, dict):
                ret.appendleft(list(node.keys())[0])
                for dep in list(node.values())[0]:
                    tmpQueue.append(dep)

    return ret


def cleanTargets(deps):
    """Builds files marked as targets from their dependencies."""
    with Progress() as progress:
        progress.console.print(f"[+] [green bold] Executing ReMakeFile for folder {getCurrentContext().cwd}.[/bold green]")
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

                if os.path.isfile(target):
                    progress.console.print(
                        f"[{job+1}/{len(deps)}] [[bold plum1]CLEAN[/bold plum1]] Cleaning dependency {target}."
                    )
                    os.remove(target)
                progress.advance(task)

    return deps


def buildTargets(deps):
    """Builds files marked as targets from their dependencies."""
    with Progress() as progress:
        progress.console.print(f"[+] [green bold] Executing ReMakeFile for folder {getCurrentContext().cwd}.[/bold green]")
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
                target, rule = dep
                if isinstance(rule, PatternRule):
                    rule = rule.expand(dep[0])

                if DRY_RUN:
                    progress.console.print(
                        f"[{job+1}/{len(deps)}] [[bold plum1]DRY-RUN[/bold plum1]] Dependency: {target} built with rule: {rule.action}"
                    )
                else:
                    progress.console.print(f"[{job+1}/{len(deps)}] {rule.actionName}")
                    rule.apply()
                progress.advance(task)

    return deps


def main():
    """Main funtion of ReMake."""
    argparser = argparse.ArgumentParser(description="ReMake is a make-like tool.")
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


html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
md2html = Builder(action="pandoc $^ -o $@")
jinja2 = Builder(action="jinja2 $^ -o $@")
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")

if __name__ == "__main__":
    main()
