#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional regarding ReMakeFile test cases."""

import os
import pathlib
import shutil
import time

from ward import test, fixture, skip

from remake import Builder, Rule, PatternRule, AddTarget, VirtualTarget
from remake import executeReMakeFileFromDirectory, buildDeps, generateDependencyList, getCurrentContext, getOldContext
from remake import setDryRun, setDevTest, unsetDryRun, unsetDevTest, setClean, unsetClean, setRebuild, unsetRebuild

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureCleanContext():
    """Cleans rules and targets and unsets dev mode and dry mode between tests."""

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    yield
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    unsetDryRun()
    unsetDevTest()


@fixture
def ensureEmptyTmp():
    """Ensures that all ReMake related files created in /tmp are emptied between tests."""

    os.chdir("/tmp")
    try:
        os.remove("/tmp/ReMakeFile")
    except FileNotFoundError:
        pass

    for f in ("/tmp/remake_subdir", "/tmp/remake_subdir2"):
        try:
            assert f.startswith("/tmp")
            shutil.rmtree(f)
        except FileNotFoundError:
            pass

    yield
    os.chdir("/tmp")

    try:
        os.remove("/tmp/ReMakeFile")
    except FileNotFoundError:
        pass

    for f in ("/tmp/remake_subdir", "/tmp/remake_subdir2"):
        try:
            assert f.startswith("/tmp")
            shutil.rmtree(f)
        except FileNotFoundError:
            pass


@test("ReMakeFile can be parsed")
def test_01_parseReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """ReMakeFile can be parsed"""

    ReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(targets="b1", deps=["a1"], builder=fooBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
AddTarget("d")
AddTarget("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    setDryRun()
    context = executeReMakeFileFromDirectory("/tmp")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(targets="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all(named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named)))
    assert pattern == [r_5]
    assert targets == [pathlib.Path("/tmp/d"), pathlib.Path("/tmp/d.foo")]


@test("Sub ReMakeFiles can be called")
def test_02_parseSubReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Sub ReMakeFiles can be called"""

    ReMakeFile = """
SubReMakeDir("/tmp/remake_subdir")
"""
    subReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(targets="b1", deps=["a1"], builder=fooBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
AddTarget("d")
AddTarget("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp/remake_subdir")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(targets="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all(named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named)))
    assert pattern == [r_5]
    assert targets == [pathlib.Path("/tmp/remake_subdir/d"), pathlib.Path("/tmp/remake_subdir/d.foo")]


@test("3 levels of subfile")
def test_03_3levelsSubReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """3 levels of subfile"""

    ReMakeFile = """
SubReMakeDir("/tmp/remake_subdir")
"""
    subReMakeFile = """
SubReMakeDir("../remake_subdir2")
"""
    subReMakeFile2 = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(targets="b1", deps=["a1"], builder=fooBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
AddTarget("d")
AddTarget("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.mkdir("/tmp/remake_subdir2")
    with open("/tmp/remake_subdir2/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile2)

    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir2")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp/remake_subdir2")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(targets="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all(named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named)))
    assert pattern == [r_5]
    assert targets == [pathlib.Path("/tmp/remake_subdir2/d"), pathlib.Path("/tmp/remake_subdir2/d.foo")]


@test("Parent rules and builders are accessible from subfile if not overriden")
def test_04_accessParentRulesFromChild(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Parent rules and builders are accessible from subfile if not overriden"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="c", deps="../b", builder=fooBuilder)
PatternRule(target="*.bar", deps="*.baz", builder=fooBuilder)
AddTarget("c")
AddTarget("c.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="b", deps="a", builder=fooBuilder)
    PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(targets="c", deps="../b", builder=fooBuilder)
    PatternRule(target="*.bar", deps="*.baz", builder=fooBuilder)
    AddTarget("c")
    AddTarget("c.foo")

    assert generateDependencyList() == context.deps


@test("Subfile can override rules")
def test_05_overrideRules(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile can override rules"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.baz", builder=fooBuilder)
AddTarget("b")
AddTarget("b.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir")
    Rule(targets="b", deps="aa", builder=fooBuilder)
    PatternRule(target="*.foo", deps="*.baz", builder=fooBuilder)
    AddTarget("b")
    AddTarget("b.foo")

    assert generateDependencyList() == context.deps


@test("Subfile rules are removed at the end of subfile (parent's rules are kept)")
def test_06_overrideParentRulesKept(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile rules are removed at the end of subfile (parent's rules are kept)"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
AddTarget("b")
AddTarget("b.foo")
del fooBuilder
"""
    subReMakeFile = """
print(fooBuilder)
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.baz", builder=fooBuilder)
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp")
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="b", deps="a", builder=fooBuilder)
    PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    AddTarget("b")
    AddTarget("b.foo")

    assert generateDependencyList() == context.deps


@test("Subfile can override rules one after another")
def test_07_overrideRulesMultipleFiles(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile can override rules one after another"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
SubReMakeDir("/tmp/remake_subdir2")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.baz", builder=fooBuilder)
AddTarget("b")
AddTarget("b.foo")
"""
    subReMakeFile2 = """
Rule(targets="b", deps="aaa", builder=fooBuilder)
PatternRule(target="*.foo", deps="*.qux", builder=fooBuilder)
AddTarget("b")
AddTarget("b.foo")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.mkdir("/tmp/remake_subdir2")
    with open("/tmp/remake_subdir2/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile2)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    context2 = getOldContext("/tmp/remake_subdir2")

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir")
    Rule(targets="b", deps="aa", builder=fooBuilder)
    PatternRule(target="*.foo", deps="*.baz", builder=fooBuilder)
    AddTarget("b")
    AddTarget("b.foo")
    assert generateDependencyList() == context.deps

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir2")
    Rule(targets="b", deps="aaa", builder=fooBuilder)
    PatternRule(target="*.foo", deps="*.qux", builder=fooBuilder)
    AddTarget("b")
    AddTarget("b.foo")
    assert generateDependencyList() == context2.deps


@test("Subfiles can access parent's deps with ../")
def test_08_accessFilesParentDir(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfiles can access parent's deps with ../"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="c", deps="../b", builder=fooBuilder)
PatternRule(target="*.baz", deps="*.bar", builder=fooBuilder)
AddTarget("c")
AddTarget("c.baz")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="b", deps="a", builder=fooBuilder)
    PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(targets="c", deps="../b", builder=fooBuilder)
    PatternRule(target="*.baz", deps="*.bar", builder=fooBuilder)
    os.chdir("/tmp")
    AddTarget("remake_subdir/c")
    AddTarget("remake_subdir/c.baz")
    assert generateDependencyList() == context.deps


@test("Parents can access subfiles targets")
def test_09_parentAccessSubfileTargets(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Parents can access subfiles targets"""

    ReMakeFile = """
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
SubReMakeDir("/tmp/remake_subdir")
Rule(targets="c", deps="/tmp/remake_subdir/b", builder=fooBuilder)
PatternRule(target="*.baz", deps="*.bar", builder=fooBuilder)
AddTarget("c")
AddTarget("c.baz")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="*.bar", deps="*.foo", builder=fooBuilder)
AddTarget("b")
AddTarget("b.baz")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp")

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="c", deps="/tmp/remake_subdir/b", builder=fooBuilder)
    PatternRule(target="*.baz", deps="*.bar", builder=fooBuilder)
    AddTarget("c")
    AddTarget("c.baz")
    assert generateDependencyList() == context.deps


@test("Detection of newer dep to rebuild target")
def test_10_detectNewerDep(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Detection of newer dep to rebuild target"""

    os.chdir("/tmp")
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    touchBuilder = Builder(action="touch $@")

    # Direct call to rule.apply
    r_1 = Rule(targets="a", deps="b", builder=touchBuilder)
    assert r_1.apply() is False
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    assert r_1.apply() is True
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Dependency graph should not changed (i) after the rule is called, and (ii) after the dep is renewed.
    pathlib.Path("/tmp/a").touch()  # Ensure target is more recent that dep.
    r_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    AddTarget("a")
    dep1 = generateDependencyList()
    r_2.apply()
    dep2 = generateDependencyList()
    assert dep1 == dep2
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    dep3 = generateDependencyList()
    assert dep1 == dep3
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Call to buildDeps
    pathlib.Path("/tmp/a").touch()  # Ensure target is more recent that dep.
    r_3 = Rule(targets="a", deps="b", builder=touchBuilder)
    AddTarget("a")
    assert buildDeps(generateDependencyList()) == []
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    assert buildDeps(generateDependencyList()) == [([pathlib.Path("/tmp/a")], r_3)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # From ReMakeFile
    pathlib.Path("/tmp/a").touch()  # Ensure target is more recent that dep.
    ReMakeFile = """
touchBuilder = Builder(action="touch $@")
Rule(targets="a", deps="b", builder=touchBuilder)
AddTarget("a")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)
    context = executeReMakeFileFromDirectory("/tmp")
    assert context.executedRules == []
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    context = executeReMakeFileFromDirectory("/tmp")
    r_4 = Rule(targets="a", deps="b", builder=touchBuilder)
    assert context.executedRules == [([pathlib.Path("/tmp/a")], r_4)]


@test("Detection of newer dep of dep (3 levels) to rebuild target")
def test_11_detectNewerDepsMultipleLevel(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Detection of newer dep of dep (3 levels) to rebuild target"""

    os.chdir("/tmp")
    touchBuilder = Builder(action="touch $@")

    # Direct call to rule.apply
    pathlib.Path("/tmp/c").touch()
    time.sleep(0.01)  # Dep is now older that intermediate dep.
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Intermedite dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    r_1_1 = Rule(targets="b", deps="c", builder=touchBuilder)
    r_1_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert r_1_1.apply() is False
    assert r_1_2.apply() is False
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    # Rule should not check dependencies of dependencies.
    # This is the job of the dependency graph!
    assert r_1_2.apply() is False
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Dependency graph should not changed (i) after the rule is called, and (ii) after the dep is renewed.
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    time.sleep(0.01)  # Dep is now older that intermediate dep.
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Intermedite dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    # Here: a more recent than b more recent than c.
    r_2_1 = Rule(targets="b", deps="c", builder=touchBuilder)
    Rule(targets="a", deps="b", builder=touchBuilder)
    AddTarget("a")
    dep1 = generateDependencyList()
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert r_2_1.apply() is False
    dep2 = generateDependencyList()
    assert dep1 == dep2
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    dep3 = generateDependencyList()
    assert dep1 == dep3
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Call to buildDeps
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    time.sleep(0.01)  # Dep is now older that intermediate dep.
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Intermedite dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    # Here: a more recent than b more recent than c.
    r_3_1 = Rule(targets="b", deps="c", builder=touchBuilder)
    r_3_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    AddTarget("a")
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert buildDeps(generateDependencyList()) == []
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    # Since dependency graph will first try to build b and c is more recent than b, b will be built.
    # Then since b just got built, b is more recent than a, and a will be built.
    assert buildDeps(generateDependencyList()) == [([pathlib.Path("/tmp/b")], r_3_1), ([pathlib.Path("/tmp/a")], r_3_2)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # From ReMakeFile
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    time.sleep(0.01)  # Dep is now older that intermediate dep.
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Intermedite dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    # Here: a more recent than b more recent than c.
    ReMakeFile = """
touchBuilder = Builder(action="touch $@")
Rule(targets="b", deps="c", builder=touchBuilder)
Rule(targets="a", deps="b", builder=touchBuilder)
AddTarget("a")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)
    context = executeReMakeFileFromDirectory("/tmp")
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert context.executedRules == []
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    # Since dependency graph will first try to build b and c is more recent than b, b will be built.
    # Then since b just got built, b is more recent than a, and a will be built.
    context = executeReMakeFileFromDirectory("/tmp")
    r_4_1 = Rule(targets="b", deps="c", builder=touchBuilder)
    r_4_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    assert context.executedRules == [([pathlib.Path("/tmp/b")], r_4_1), ([pathlib.Path("/tmp/a")], r_4_2)]


@test("Making specific targets")
def test_12_specificTargets(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Making specific targets"""

    ReMakeFile = """
touchBuilder = Builder(action="touch $@")
Rule(targets="d", deps=["c", "a2", "b1"], builder=touchBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=touchBuilder)
Rule(targets="b1", deps=["a1"], builder=touchBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=touchBuilder)
PatternRule(target="*.foo", deps="*.bar", builder=touchBuilder)
PatternRule(target="*.bar", deps="*.baz", builder=touchBuilder)
Rule(targets="e", deps=["f", "g"], builder=touchBuilder)  
Rule(targets="f", deps=["f1", "f2"], builder=touchBuilder)
PatternRule(target="*.alpha", deps="*.beta", builder=touchBuilder)
PatternRule(target="*.beta", deps="*.gamma", builder=touchBuilder)
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    setDryRun()

    touchBuilder = Builder(action="touch $@")
    r_1 = Rule(targets="d", deps=["c", "a2", "b1"], builder=touchBuilder)
    r_2 = Rule(targets="c", deps=["b1", "b2"], builder=touchBuilder)
    r_3 = Rule(targets="b1", deps=["a1"], builder=touchBuilder)
    r_4 = Rule(targets="b2", deps=["a1", "a2"], builder=touchBuilder)
    r_5 = PatternRule(target="*.foo", deps="*.bar", builder=touchBuilder)
    r_6 = PatternRule(target="*.bar", deps="*.baz", builder=touchBuilder)
    Rule(targets="e", deps=["f", "g"], builder=touchBuilder)
    r_7 = Rule(targets="f", deps=["f1", "f2"], builder=touchBuilder)
    PatternRule(target="*.alpha", deps="*.beta", builder=touchBuilder)
    r_8 = PatternRule(target="*.beta", deps="*.gamma", builder=touchBuilder)

    # First with final targets.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/d"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1)
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.foo"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo')))
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # With intermediate targets.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/c"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2)
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.bar"])
    assert context.executedRules == [([pathlib.Path("/tmp/test.bar")], r_6.expand(pathlib.Path("/tmp/test.bar")))]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # With unknown targets.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/unknown"])
    assert context.executedRules == []
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.unknown"])
    assert context.executedRules == []
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Mixed (final and non-related intermediate) in both orders.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/d", "/tmp/f"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
        ([pathlib.Path("/tmp/f")],
         r_7),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.foo", "/tmp/test.beta"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
        ([pathlib.Path('/tmp/test.beta')],
         r_8.expand(pathlib.Path('/tmp/test.beta'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/f", "/tmp/d"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/f")],
         r_7),
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.beta", "/tmp/test.foo"])
    assert context.executedRules == [
        ([pathlib.Path('/tmp/test.beta')],
         r_8.expand(pathlib.Path('/tmp/test.beta'))),
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Mixed (final and related intermediate) in both orders.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/d", "/tmp/c"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.foo", "/tmp/test.bar"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/c", "/tmp/d"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.bar", "/tmp/test.foo"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Mixed (any correct target with unkown) in both orders.
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/d", "/tmp/unkown"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.foo", "/tmp/test.unknown"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/unknown", "/tmp/d"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/b2")],
         r_4),
        ([pathlib.Path("/tmp/b1")],
         r_3),
        ([pathlib.Path("/tmp/c")],
         r_2),
        ([pathlib.Path("/tmp/d")],
         r_1),
    ]
    context = executeReMakeFileFromDirectory("/tmp", targets=["/tmp/test.unknown", "/tmp/test.foo"])
    assert context.executedRules == [
        ([pathlib.Path("/tmp/test.bar")],
         r_6.expand(pathlib.Path("/tmp/test.bar"))),
        ([pathlib.Path('/tmp/test.foo')],
         r_5.expand(pathlib.Path('/tmp/test.foo'))),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # TODO VirtualTarget


@test("Cleaning targets")
def test_13_clean_targets(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Cleaning targets"""

    os.chdir("/tmp")
    ReMakeFile = """
touchBuilder = Builder(action="touch $@")
Rule(targets="a", deps="b", builder=touchBuilder)
Rule(targets="b", deps=[], builder=touchBuilder)
AddTarget("a")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    # 1. Build targets
    executeReMakeFileFromDirectory("/tmp")
    assert pathlib.Path("/tmp/a").exists()
    assert pathlib.Path("/tmp/b").exists()

    # 2. Clean targets
    setClean()
    executeReMakeFileFromDirectory("/tmp")
    assert not pathlib.Path("/tmp/a").exists()
    assert not pathlib.Path("/tmp/b").exists()
    unsetClean()


@test("Rebuilding targets")
def test_14_rebuild_targets(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Rebuilding targets"""

    os.chdir("/tmp")
    ReMakeFile = """
touchBuilder = Builder(action="touch $@")
Rule(targets="a", deps="b", builder=touchBuilder)
Rule(targets="b", deps=[], builder=touchBuilder)
AddTarget("a")
"""
    with open("/tmp/ReMakeFile", "w+", encoding="utf-8") as handle:
        handle.write(ReMakeFile)

    # 1. Build targets
    executeReMakeFileFromDirectory("/tmp")
    assert pathlib.Path("/tmp/a").exists()
    assert pathlib.Path("/tmp/b").exists()
    a_mtime = pathlib.Path("/tmp/a").stat().st_mtime
    b_mtime = pathlib.Path("/tmp/b").stat().st_mtime
    time.sleep(0.01)

    # 2. Rebuild targets
    setRebuild()
    executeReMakeFileFromDirectory("/tmp")
    assert pathlib.Path("/tmp/a").exists()
    assert pathlib.Path("/tmp/b").exists()
    assert pathlib.Path("/tmp/a").stat().st_mtime > a_mtime
    assert pathlib.Path("/tmp/b").stat().st_mtime > b_mtime
    unsetRebuild()
