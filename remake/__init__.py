#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "v1.1.0+6450831"

from remake.main import AddTarget, AddVirtualTarget
from remake.rules import Rule, PatternRule
from remake.paths import VirtualDep, VirtualTarget, GlobPattern
from remake.builders import Builder
from remake.main import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, buildDeps, cleanDeps
from remake.context import setDryRun, setVerbose, setDevTest, unsetDryRun, unsetVerbose, unsetDevTest
from remake.context import getCurrentContext, getOldContext
