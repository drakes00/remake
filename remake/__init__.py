#!/usr/bin/env python
# -*- coding: utf-8 -*-

from remake.main import Target, Builder, Rule, PatternRule
from remake.main import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, buildDeps
from remake.main import setDryRun, setVerbose, setDevTest, unsetDryRun, unsetVerbose, unsetDevTest
from remake.context import getCurrentContext, getOldContext
