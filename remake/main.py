#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main funtions of ReMake."""

import argparse
import os
import re
import subprocess

from collections import deque
from rich.progress import Console, Progress

from remake.rules import Rule, PatternRule, getRules
from remake.builders import Builder, html2pdf_chrome, md2html, jinja2, pdfcrop

TARGETS = []
VERBOSE = False
DRY_RUN = False


class Target():
    """Class registering files as remake targets."""
    def __init__(self, target):
        global TARGETS
        if isinstance(target, list):
            TARGETS += target
        else:
            TARGETS += [target]


def getTargets():
    """Returns the list of targets to build."""
    return TARGETS


def clearTargets():
    """Clears list of targets."""
    global TARGETS
    TARGETS = []


class SubReMakeDir():
    def __init__(self, subDir):
        subprocess.run(["remake"], cwd=subDir)


def loadScript():
    """Loads and execs the ReMakeFile script."""
    with open("ReMakeFile", "r") as handle:
        script = handle.read()

    exec(script)


def buildTargets():
    """Builds files marked as targets from their dependencies."""
    deps = []
    for target in TARGETS:
        deps += [findBuildPath(target)]

    deps = sortDeps(deps)
    with Progress() as progress:
        task = progress.add_task("ReMakeFile steps", total=len(deps))
        for job, dep in enumerate(deps):
            if isinstance(dep, str):
                target = dep
            elif isinstance(dep, tuple):
                target = dep[0]

            if os.path.isfile(target):
                progress.console.print(
                    f"[{job+1}/{len(deps)}] [[bold plum1]SKIP[/bold plum1]] Dependency {target} already exists."
                )
                progress.advance(task)
            else:
                assert isinstance(dep, tuple)
                rule = dep[1]
                if isinstance(rule, PatternRule):
                    rule = rule.expand(dep[0])

                progress.console.print(f"[{job+1}/{len(deps)}] {rule.actionName}")
                if VERBOSE:
                    progress.console.print(rule.action)
                if DRY_RUN is False:
                    rule.apply()
                progress.advance(task)


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


def findBuildPath(target):
    """Constructs dependency graph from registered rules."""
    if os.path.isfile(target):
        return target

    depNames = []
    foundRule = None
    namedRules, patternRules = getRules()
    for rule in namedRules:
        occ = re.match(rule.target, target)
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
        occ = re.match(regex+"$", target)
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

    Console().print(
        f"[[red bold]FAILED[/red bold]] Unable to find build path for [light_slate_blue]{target}[/light_slate_blue]! Aborting!"
    )
    return target


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
