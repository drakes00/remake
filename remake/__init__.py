#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = "v1.1.0+6450831"

from remake.main import AddTarget, Builder, Rule, PatternRule, VirtualDep, VirtualTarget, AddVirtualTarget, GlobPattern
from remake.main import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, buildDeps, cleanDeps
from remake.main import setDryRun, setVerbose, setDevTest, unsetDryRun, unsetVerbose, unsetDevTest
from remake.context import getCurrentContext, getOldContext
