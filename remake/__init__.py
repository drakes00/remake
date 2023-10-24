#!/usr/bin/env python
# -*- coding: utf-8 -*-

from remake.main import AddTarget, Builder, Rule, PatternRule, VirtualDep, VirtualTarget, AddVirtualTarget
from remake.main import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, buildDeps, cleanDeps
from remake.main import setDryRun, setVerbose, setDevTest, unsetDryRun, unsetVerbose, unsetDevTest
from remake.context import getCurrentContext, getOldContext
