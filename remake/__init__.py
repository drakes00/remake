#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "v1.2.0+adf36a7"

from remake.main import AddTarget, AddVirtualTarget
from remake.rules import Rule, PatternRule
from remake.paths import VirtualDep, VirtualTarget, GlobPattern
from remake.builders import Builder
from remake.main import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, buildDeps, cleanDeps
from remake.context import getCurrentContext, getOldContext
from remake.context import setVerbose, unsetVerbose, isVerbose
from remake.context import setDryRun, unsetDryRun, isDryRun
from remake.context import setDevTest, unsetDevTest, isDevTest
from remake.context import setClean, unsetClean, isClean, setRebuild, unsetRebuild, isRebuild
