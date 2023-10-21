#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pathlib
import shutil
import time

from ward import test, raises, fixture

from remake import Builder, Rule, PatternRule, Target, VirtualTarget, VirtualDep
from remake import findBuildPath, executeReMakeFileFromDirectory, buildDeps, cleanDeps, generateDependencyList, getCurrentContext, getOldContext
from remake import setDryRun, setDevTest, unsetDryRun, unsetDevTest

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


@test("Automatically detect dependencies")
def test_01_funDeps(_=ensureCleanContext):
    """Automatically detect dependencies"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    r_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_1): [VirtualDep("b")]
    }
    getCurrentContext().clearRules()

    # Two files one dependence.
    r_2_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("c"), builder=fooBuilder)
    r_2_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_2_1): [VirtualDep("c")]
    }
    assert findBuildPath("b") == {
        ("b",
         r_2_2): [VirtualDep("c")]
    }
    getCurrentContext().clearRules()

    # One file two dependencies
    r_3_1 = Rule(targets=VirtualTarget("a"), deps=[VirtualDep("b"), VirtualDep("c")], builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_3_1): [VirtualDep("b"),
                  VirtualDep("c")]
    }
    getCurrentContext().clearRules()

    # One file two dependencies with two rules.
    # r_4_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    # r_4_2 = Rule(targets="a", deps="c", builder=fooBuilder)
    # FIXME Should raise or r_4_2 should replace r_4_1
    # assert findBuildPath("a") == {("/tmp/a", r_4_1): ["/tmp/b", "/tmp/c"]}
    # getCurrentContext().clearRules()

    # Three levels
    r_5_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    r_5_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_5_1): [{
            (VirtualDep("b"),
             r_5_2): [VirtualDep("c")]
        }]
    }
    getCurrentContext().clearRules()

    # Complex
    r_6_1 = Rule(
        targets=VirtualTarget("d"),
        deps=[
            VirtualDep("c"),
            VirtualDep("a2"),
            VirtualDep("b1"),
        ],
        builder=fooBuilder,
    )
    r_6_2 = Rule(
        targets=VirtualTarget("c"),
        deps=[
            VirtualDep("b1"),
            VirtualDep("b2"),
        ],
        builder=fooBuilder,
    )
    r_6_3 = Rule(
        targets=VirtualTarget("b1"),
        deps=[
            VirtualDep("a1"),
        ],
        builder=fooBuilder,
    )
    r_6_4 = Rule(
        targets=VirtualTarget("b2"),
        deps=[
            VirtualDep("a1"),
            VirtualDep("a2"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath("d") == {
        ("d",
         r_6_1):
            [
                {
                    (VirtualDep("c"),
                     r_6_2):
                        [
                            {
                                (VirtualDep("b1"),
                                 r_6_3): [VirtualDep("a1")]
                            },
                            {
                                (VirtualDep("b2"),
                                 r_6_4): [VirtualDep("a1"),
                                          VirtualDep("a2")]
                            }
                        ]
                },
                VirtualDep("a2"),
                {
                    (VirtualDep("b1"),
                     r_6_3): [VirtualDep("a1")]
                }
            ]
    }
    getCurrentContext().clearRules()

    # Simple rule with another rule with multiple targets
    r_8_1 = Rule(targets=[VirtualTarget("a"), VirtualTarget("b")], deps=VirtualDep("c"), builder=fooBuilder)
    r_8_2 = Rule(targets=VirtualTarget("d"), deps=[VirtualDep("e"), VirtualDep("f")], builder=fooBuilder)
    r_8_3 = Rule(
        targets=[
            VirtualTarget("g"),
            VirtualTarget("h"),
        ],
        deps=[
            VirtualDep("i"),
            VirtualDep("j"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath("a") == {
        ("a",
         r_8_1): [VirtualDep("c")]
    }
    assert findBuildPath("b") == {
        ("b",
         r_8_1): [VirtualDep("c")]
    }
    assert findBuildPath("d") == {
        ("d",
         r_8_2): [
            VirtualDep("e"),
            VirtualDep("f"),
        ]
    }
    assert findBuildPath("g") == {
        ("g",
         r_8_3): [
            VirtualDep("i"),
            VirtualDep("j"),
        ]
    }
    assert findBuildPath("h") == {
        ("h",
         r_8_3): [
            VirtualDep("i"),
            VirtualDep("j"),
        ]
    }
    getCurrentContext().clearRules()


@test("Dependency can appear multiple times in the tree")
def test_02_funDepsMultipleTimes(_=ensureCleanContext):
    """Dependency can appear multiple times in the tree"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    r_1 = Rule(targets=VirtualTarget("a"), deps=[VirtualDep("b"), VirtualDep("c")], builder=fooBuilder)
    r_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_1): [{
            (VirtualDep("b"),
             r_2): [VirtualDep("c")]
        },
                VirtualDep("c")]
    }


@test("Same rule applied twice should be ignored")
def test_03_funSameRuleTwice(_=ensureCleanContext):
    """Same rule applied twice should be ignored"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    r_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    r_2 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert findBuildPath("a") == {
        ("a",
         r_1): [VirtualDep("b")]
    }


@test("Rules must make targets")
def test_04_funMakeTarget(_=ensureCleanContext):
    """Rules must make targets"""

    fooBuilder = Builder(action="ls > /dev/null")
    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # Ensure rule not making the target file will throw.
    rule = Rule(targets=f"{TMP_FILE}", deps=[], builder=fooBuilder)
    with raises(FileNotFoundError):
        rule.apply(None)
    getCurrentContext().clearRules()

    rule = Rule(targets=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    rule.apply(None)
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)


@test("ReMakeFile can be parsed")
def test_05_parseReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """ReMakeFile can be parsed"""

    ReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(targets="b1", deps=["a1"], builder=fooBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
Target("d")
Target("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    setDryRun()
    setDevTest()
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
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["/tmp/d", "/tmp/d.foo"]


@test("Sub ReMakeFiles can be called")
def test_06_parseSubReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Sub ReMakeFiles can be called"""

    ReMakeFile = f"""
SubReMakeDir("/tmp/remake_subdir")
"""
    subReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(targets="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(targets="b1", deps=["a1"], builder=fooBuilder)
Rule(targets="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
Target("d")
Target("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
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
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["/tmp/remake_subdir/d", "/tmp/remake_subdir/d.foo"]


@test("3 levels of subfile")
def test_07_3levelsSubReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """3 levels of subfile"""

    ReMakeFile = f"""
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
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
Target("d")
Target("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)

    os.mkdir("/tmp/remake_subdir2")
    with open("/tmp/remake_subdir2/ReMakeFile", "w+") as handle:
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
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["/tmp/remake_subdir2/d", "/tmp/remake_subdir2/d.foo"]


@test("Parent rules and builders are accessible from subfile if not overriden")
def test_08_accessParentRulesFromChild(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Parent rules and builders are accessible from subfile if not overriden"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="c", deps="b", builder=fooBuilder)
PatternRule(target="%.bar", deps="%.baz", builder=fooBuilder)
Target("c")
Target("c.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="b", deps="a", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(targets="c", deps="b", builder=fooBuilder)
    PatternRule(target="%.bar", deps="%.baz", builder=fooBuilder)
    Target("c")
    Target("c.foo")

    assert generateDependencyList() == context.deps


@test("Subfile can override rules")
def test_09_overrideRules(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile can override rules"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
Target("b")
Target("b.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp/remake_subdir")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir")
    Rule(targets="b", deps="aa", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
    Target("b")
    Target("b.foo")

    assert generateDependencyList() == context.deps


@test("Subfile rules are removed at the end of subfile (parent's rules are kept)")
def test_10_overrideParentRulesKeps(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile rules are removed at the end of subfile (parent's rules are kept)"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
Target("b")
Target("b.foo")
del fooBuilder
"""
    subReMakeFile = """
print(fooBuilder)
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    setDevTest()
    executeReMakeFileFromDirectory("/tmp")
    context = getOldContext("/tmp")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    Rule(targets="b", deps="a", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    Target("b")
    Target("b.foo")

    assert generateDependencyList() == context.deps


@test("Subfile can override rules one after another")
def test_11_overrideRulesMultipleFiles(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfile can override rules one after another"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
SubReMakeDir("/tmp/remake_subdir2")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="aa", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
Target("b")
Target("b.foo")
"""
    subReMakeFile2 = """
Rule(targets="b", deps="aaa", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.qux", builder=fooBuilder)
Target("b")
Target("b.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)

    os.mkdir("/tmp/remake_subdir2")
    with open("/tmp/remake_subdir2/ReMakeFile", "w+") as handle:
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
    PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
    Target("b")
    Target("b.foo")
    assert generateDependencyList() == context.deps

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir2")
    Rule(targets="b", deps="aaa", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.qux", builder=fooBuilder)
    Target("b")
    Target("b.foo")
    assert generateDependencyList() == context2.deps


@test("Subfiles can access parent's deps with ../")
def test_12_accessFilesParentDir(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Subfiles can access parent's deps with ../"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.bar", deps="%.foo", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="c", deps="../b", builder=fooBuilder)
PatternRule(target="%.baz", deps="%.bar", builder=fooBuilder)
Target("c")
Target("c.baz")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
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
    PatternRule(target="%.bar", deps="%.foo", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(targets="c", deps="../b", builder=fooBuilder)
    PatternRule(target="%.baz", deps="%.bar", builder=fooBuilder)
    os.chdir("/tmp")
    Target("remake_subdir/c")
    Target("remake_subdir/c.baz")
    assert generateDependencyList() == context.deps


@test("Parents can access subfiles targets")
def test_13_parentAccessSubfileTargets(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Parents can access subfiles targets"""

    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
SubReMakeDir("/tmp/remake_subdir")
Rule(targets="c", deps="/tmp/remake_subdir/b", builder=fooBuilder)
PatternRule(target="%.baz", deps="%.bar", builder=fooBuilder)
Target("c")
Target("c.baz")
del fooBuilder
"""
    subReMakeFile = """
Rule(targets="b", deps="a", builder=fooBuilder)
PatternRule(target="%.bar", deps="%.foo", builder=fooBuilder)
Target("b")
Target("b.baz")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
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
    PatternRule(target="%.baz", deps="%.bar", builder=fooBuilder)
    Target("c")
    Target("c.baz")
    assert generateDependencyList() == context.deps


@test("Can generate all targets from a pattern rule (with a glob call)")
def test_14_generateAllTargetsOfPatternRules(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Can generate all targets from a pattern rule (with a glob call)"""

    os.mkdir("/tmp/remake_subdir")
    os.mkdir("/tmp/remake_subdir/foo")
    os.mkdir("/tmp/remake_subdir/foo/bar")
    open("/tmp/remake_subdir/non.x", "w+")
    open("/tmp/remake_subdir/foo/a.x", "w+")
    open("/tmp/remake_subdir/foo/b.x", "w+")
    open("/tmp/remake_subdir/foo/bar/c.x", "w+")
    open("/tmp/remake_subdir/foo/bar/d.x", "w+")

    os.chdir("/tmp/remake_subdir/foo")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    rule = PatternRule(target="%.y", deps="%.x", builder=fooBuilder)
    assert sorted(rule.allTargets) == sorted(
        [pathlib.Path("a.y"),
         pathlib.Path("b.y"),
         pathlib.Path("bar/c.y"),
         pathlib.Path("bar/d.y")]
    )


@test("Automatically detect dependencies with multiple targets")
def test_15_funDepsMultipleTargets(_=ensureCleanContext):
    """Automatically detect dependencies with multiple targets"""

    setDryRun()
    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # Two targets same rule.
    r_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    Target("a")
    Target("b")
    assert generateDependencyList() == ["/tmp/c", (("/tmp/a", "/tmp/b"), r_1)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two targets same rule (no deps).
    r_2 = Rule(targets=["a", "b"], builder=fooBuilder)
    Target("a")
    Target("b")
    assert generateDependencyList() == [(("/tmp/a", "/tmp/b"), r_2)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Three targets same rule.
    r_3 = Rule(targets=["a", "b", "c"], deps="d", builder=fooBuilder)
    Target("a")
    Target("b")
    Target("c")
    assert generateDependencyList() == ["/tmp/d", (("/tmp/a", "/tmp/b", "/tmp/c"), r_3)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two targets two same rules.
    r_4_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_4_2 = Rule(targets=["d", "e"], deps="f", builder=fooBuilder)
    Target("a")
    Target("b")
    Target("d")
    Target("e")
    assert generateDependencyList() == [
        "/tmp/c",
        (("/tmp/a",
          "/tmp/b"),
         r_4_1),
        "/tmp/f",
        (("/tmp/d",
          "/tmp/e"),
         r_4_2)
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two levels.
    r_5_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_5_2 = Rule(targets=["d", "e"], deps="a", builder=fooBuilder)
    Target("a")
    Target("b")
    Target("d")
    Target("e")
    assert generateDependencyList() == ["/tmp/c", (("/tmp/a", "/tmp/b"), r_5_1), (("/tmp/d", "/tmp/e"), r_5_2)]


@test("Rule with multiple targets is executed only once to make all targets")
def test_16_ruleMultipleTargetsExecutedOnce(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Rule with multiple targets is executed only once to make all targets"""

    setDevTest()
    setDryRun()
    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_2 = Rule(targets=["d", "e"], deps="a", builder=fooBuilder)
    Target("a")
    Target("b")
    Target("d")
    Target("e")
    os.chdir("/tmp")
    assert buildDeps(generateDependencyList()) == [(("/tmp/a", "/tmp/b"), r_1), (("/tmp/d", "/tmp/e"), r_2)]


@test("Dependencies can be cleaned")
def test_17_cleanDependencies(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Dependencies can be cleaned"""

    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    r_1 = Rule(targets=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    Target(TMP_FILE)
    assert buildDeps(generateDependencyList()) == [(TMP_FILE, r_1)]
    assert os.path.isfile(TMP_FILE)
    assert cleanDeps(generateDependencyList()) == [(TMP_FILE, r_1)]
    assert not os.path.isfile(TMP_FILE)


@test("Detection of newer dep to rebuild target")
def test_18_detectNewerDep(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Detection of newer dep to rebuild target"""

    os.chdir("/tmp")
    pathlib.Path("/tmp/b").touch()
    time.sleep(0.01)  # Dep is now older that target.
    pathlib.Path("/tmp/a").touch()
    touchBuilder = Builder(action="touch $@")

    # Direct call to rule.apply
    r_1 = Rule(targets="a", deps="b", builder=touchBuilder)
    assert r_1.apply(None) == False
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    assert r_1.apply(None) == True
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Dependency graph should not changed (i) after the rule is called, and (ii) after the dep is renewed.
    pathlib.Path("/tmp/a").touch()  # Ensure target is more recent that dep.
    r_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    Target("a")
    dep1 = generateDependencyList()
    r_2.apply(None)
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
    Target("a")
    assert buildDeps(generateDependencyList()) == []
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    assert buildDeps(generateDependencyList()) == [("/tmp/a", r_3)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # From ReMakeFile
    pathlib.Path("/tmp/a").touch()  # Ensure target is more recent that dep.
    ReMakeFile = f"""
touchBuilder = Builder(action="touch $@")
Rule(targets="a", deps="b", builder=touchBuilder)
Target("a")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)
    context = executeReMakeFileFromDirectory("/tmp")
    assert context.executedRules == []
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    time.sleep(0.01)
    pathlib.Path("/tmp/b").touch()
    context = executeReMakeFileFromDirectory("/tmp")
    r_4 = Rule(targets="a", deps="b", builder=touchBuilder)
    assert context.executedRules == [("/tmp/a", r_4)]


@test("Detection of newer dep of dep (3 levels) to rebuild target")
def test_19_detectNewerDepsMultipleLevel(_=ensureCleanContext, _2=ensureEmptyTmp):
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
    assert r_1_1.apply(None) == False
    assert r_1_2.apply(None) == False
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    # Rule should not check dependencies of dependencies.
    # This is the job of the dependency graph!
    assert r_1_2.apply(None) == False
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
    r_2_2 = Rule(targets="a", deps="b", builder=touchBuilder)
    Target("a")
    dep1 = generateDependencyList()
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert r_2_1.apply(None) == False
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
    Target("a")
    # Here: a more recent than b more recent than c.
    # Nothing to do, rules are expected to return False.
    assert buildDeps(generateDependencyList()) == []
    time.sleep(0.01)
    pathlib.Path("/tmp/c").touch()
    # Here: c more recent than a more recent than b.
    # Since dependency graph will first try to build b and c is more recent than b, b will be built.
    # Then since b just got built, b is more recent than a, and a will be built.
    assert buildDeps(generateDependencyList()) == [("/tmp/b", r_3_1), ("/tmp/a", r_3_2)]
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
    ReMakeFile = f"""
touchBuilder = Builder(action="touch $@")
Rule(targets="b", deps="c", builder=touchBuilder)
Rule(targets="a", deps="b", builder=touchBuilder)
Target("a")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
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
    assert context.executedRules == [("/tmp/b", r_4_1), ("/tmp/a", r_4_2)]
