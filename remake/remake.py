#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import subprocess
import sys

from rich.progress import Console, Progress

NAMED_RULES = []
PATTERN_RULES = []
TARGETS = []
VERBOSE = False
DRY_RUN = False
PROGRESS = None


class Rule(object):
    _deps = None
    _target = None
    _action = None

    def __init__(self, deps, target, builder):
        try:
            deps.pop
            self._deps = deps
        except AttributeError:
            self._deps = [deps]

        self._target = target
        self._action = builder._parseAction(self._deps, self._target)

        global NAMED_RULES
        NAMED_RULES += [self]

    def apply(self):
        try:
            self._action(self._deps, self._target)
        except TypeError:
            subprocess.run(self._action)

    @property
    def action(self):
        if isinstance(self._action, list):
            return " ".join(self._action)
        else:
            return f"{self._action}({self._deps}, {self._target})"

    @property
    def actionName(self):
        if isinstance(self._action, list):
            return " ".join(self._action)
        elif self._action.__doc__ is not None:
            return self._action.__doc__
        else:
            return f"{self._action}({self._deps}, {self._target})"

    @property
    def target(self):
        return self._target

    @property
    def deps(self):
        return self._deps


class PatternRule(Rule):
    def __init__(self, deps, target, builder):
        try:
            deps.pop
            self._deps = deps
        except AttributeError:
            self._deps = [deps]

        self._target = target
        self._action = builder._parseAction(self._deps, self._target)

        assert self._target.startswith("%")
        for dep in self._deps:
            assert dep.startswith("%")

        global PATTERN_RULES
        PATTERN_RULES += [self]


class Builder(object):
    _action = None

    def __init__(self, action):
        self._action = action

    def _parseAction(self, deps, target):
        if isinstance(self._action, str):
            ret = self._action
            ret = ret.replace("$^", " ".join(deps))
            ret = ret.replace("$@", target)
            ret = ret.split(" ")
            return ret
        else:
            return self._action

    @property
    def action(self):
        return self._action


class Target(object):
    def __init__(self, target):
        global TARGETS
        if isinstance(target, list):
            TARGETS += target
        else:
            TARGETS += [target]


def loadScript():
    with open("ReMakeFile", "r") as handle:
        script = handle.read()

    exec(script)


def applyRules():
    with Progress() as progress:
        global PROGRESS
        PROGRESS = progress
        task = progress.add_task("Compilation steps", total=len(RULES))
        for job, rule in enumerate(RULES):
            if os.path.isfile(rule.target):
                progress.console.print(
                    f"[{job+1}/{len(RULES)}] [[bold plum1]SKIP[/bold plum1]] {rule.actionName}"
                )
                progress.advance(task)
            else:
                progress.console.print(f"[{job+1}/{len(RULES)}] {rule.actionName}")
                if VERBOSE:
                    PROGRESS.console.print(rule.action)
                if DRY_RUN is False:
                    rule.apply()
                progress.advance(task)


def buildTargets():
    deps = []
    for target in TARGETS:
        deps += [findBuildPath(target)]

    from rich.pretty import pprint
    pprint(deps, expand_all=True)


def findBuildPath(target):
    if os.path.isfile(target):
        return target
    else:
        depNames = []
        for rule in NAMED_RULES:
            occ = re.match(rule._target, target)
            if occ:
                # Target found in rule's target.
                depNames += rule._deps

        # Stopping here is named rule was found.
        if depNames != []:
            return {target: [findBuildPath(dep) for dep in depNames]}

        for rule in PATTERN_RULES:
            regex = rule._target.replace("%", "([a-zA-Z0-9_/-]*)")
            occ = re.match(regex, target)
            if occ:
                # Rule was an anonymous rule (with %).
                # Expanding rule to generate deps file names.
                for dep in rule._deps:
                    depName = occ.expand(dep.replace("%", r"\1"))
                    depNames += [depName]

        if depNames != []:
            return {target: [findBuildPath(dep) for dep in depNames]}
        else:
            Console().print(
                f"[[red bold]FAILED[/red bold]] Unable to find build path for [light_slate_blue]{target}[/light_slate_blue]! Aborting!"
            )
            sys.exit(1)


def main():
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
    args = argparser.parse_args()

    global VERBOSE, DRY_RUN
    if args.verbose:
        VERBOSE = True
    if args.dry_run:
        DRY_RUN = True
        VERBOSE = True

    loadScript()
    buildTargets()


if __name__ == "__main__":
    main()
