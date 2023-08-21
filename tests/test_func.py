#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pathlib
import shutil
from ward import test, raises, fixture

from remake import Builder, Rule, PatternRule, Target
from remake import findBuildPath, executeReMakeFileFromDirectory, generateDependencyList, getCurrentContext, getOldContext
from remake import setDryRun, setDevTest, unsetDryRun, unsetDevTest

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureCleanContext():
    getCurrentContext().clearRules()
    yield
    getCurrentContext().clearRules()
    unsetDryRun()
    unsetDevTest()


@fixture
def ensureEmptyTmp():
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
    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    r_1 = Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_1): ["/tmp/b"]
    }
    getCurrentContext().clearRules()

    # Two files one dependence.
    r_2_1 = Rule(target="a", deps="c", builder=fooBuilder)
    r_2_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_2_1): ["/tmp/c"]
    }
    assert findBuildPath("b") == {
        ("/tmp/b",
         r_2_2): ["/tmp/c"]
    }
    getCurrentContext().clearRules()

    # One file two dependencies
    r_3_1 = Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_3_1): ["/tmp/b",
                  "/tmp/c"]
    }
    getCurrentContext().clearRules()

    # One file two dependencies with two rules.
    #FIXME Detect ambigous build paths!
    #r_4_1 = Rule(target="a", deps="b", builder=fooBuilder)
    #r_4_2 = Rule(target="a", deps="c", builder=fooBuilder)
    #assert findBuildPath("a") == {("a": ["b", "c"]}
    #getCurrentContext().clearRules()

    # Three levels
    r_5_1 = Rule(target="a", deps="b", builder=fooBuilder)
    r_5_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_5_1): [{
            ("/tmp/b",
             r_5_2): ["/tmp/c"]
        }]
    }
    getCurrentContext().clearRules()

    # Complex
    r_6_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_6_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_6_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_6_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    assert findBuildPath("d") == {
        ("/tmp/d",
         r_6_1):
            [
                {
                    ("/tmp/c",
                     r_6_2): [{
                        ("/tmp/b1",
                         r_6_3): ["/tmp/a1"]
                    },
                              {
                                  ("/tmp/b2",
                                   r_6_4): ["/tmp/a1",
                                            "/tmp/a2"]
                              }]
                },
                "/tmp/a2",
                {
                    ("/tmp/b1",
                     r_6_3): ["/tmp/a1"]
                }
            ]
    }


@test("Dependency can appear multiple times in the tree")
def test_02_funDepsMultipleTimes(_=ensureCleanContext):
    """Dependency can appear multiple times in the tree"""
    fooBuilder = Builder(action="Magically creating $@ from $<")

    os.chdir("/tmp")
    r_1 = Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    r_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_1): [{
            ("/tmp/b",
             r_2): ["/tmp/c"]
        },
                "/tmp/c"]
    }


@test("Same rule applied twice should be ignored")
def test_03_funSameRuleTwice(_=ensureCleanContext):
    """Same rule applied twice should be ignored"""
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    os.chdir("/tmp")
    r_1 = Rule(target="a", deps="b", builder=fooBuilder)
    r_2 = Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {
        ("/tmp/a",
         r_1): ["/tmp/b"]
    }


@test("Rules must make target")
def test_04_funMakeTarget(_=ensureCleanContext):
    """Rules must make target"""
    fooBuilder = Builder(action="ls > /dev/null")
    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # Ensure rule not making the target file will throw.
    rule = Rule(target=f"{TMP_FILE}", deps=[], builder=fooBuilder)
    with raises(FileNotFoundError):
        rule.apply(None)
    getCurrentContext().clearRules()

    rule = Rule(target=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    rule.apply(None)
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)


@test("ReMakeFile can be parsed")
def test_05_parseReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """ReMakeFile can be parsed"""
    ReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(target="b1", deps=["a1"], builder=fooBuilder)
Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
Target("d")
Target("d.foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.chdir("/tmp")
    setDryRun()
    context = executeReMakeFileFromDirectory("/tmp")
    named, pattern = context.rules
    targets = context.targets
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    Target("d")
    Target("d.foo")

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["d", "d.foo"]


@test("Sub ReMakeFiles can be called")
def test_06_parseSubReMakeFile(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Sub ReMakeFiles can be called"""
    ReMakeFile = f"""
SubReMakeDir("/tmp/remake_subdir")
"""
    subReMakeFile = """
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(target="b1", deps=["a1"], builder=fooBuilder)
Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
Target("d")
Target("d.foo")
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

    os.chdir("/tmp/remake_subdir")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    Target("d")
    Target("d.foo")

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["d", "d.foo"]


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
Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
Rule(target="b1", deps=["a1"], builder=fooBuilder)
Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
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

    os.chdir("/tmp")
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
    r_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    Target("d")
    Target("d.foo")

    assert len(named) == 4 and len(pattern) == 1
    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["d", "d.foo"]


@test("Parent rules and builders are accessible from subfile if not overriden")
def test_08_accessParentRulesFromChild(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Parent rules and builders are accessible from subfile if not overriden"""
    ReMakeFile = f"""
global fooBuilder
fooBuilder = Builder(action="Magically creating $@ from $<")
Rule(target="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(target="c", deps="b", builder=fooBuilder)
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
    Rule(target="b", deps="a", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(target="c", deps="b", builder=fooBuilder)
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
Rule(target="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(target="b", deps="aa", builder=fooBuilder)
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
    Rule(target="b", deps="aa", builder=fooBuilder)
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
Rule(target="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
Target("b")
Target("b.foo")
del fooBuilder
"""
    subReMakeFile = """
print(fooBuilder)
Rule(target="b", deps="aa", builder=fooBuilder)
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
    Rule(target="b", deps="a", builder=fooBuilder)
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
Rule(target="b", deps="a", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
SubReMakeDir("/tmp/remake_subdir2")
del fooBuilder
"""
    subReMakeFile = """
Rule(target="b", deps="aa", builder=fooBuilder)
PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
Target("b")
Target("b.foo")
"""
    subReMakeFile2 = """
Rule(target="b", deps="aaa", builder=fooBuilder)
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
    Rule(target="b", deps="aa", builder=fooBuilder)
    PatternRule(target="%.foo", deps="%.baz", builder=fooBuilder)
    Target("b")
    Target("b.foo")
    assert generateDependencyList() == context.deps

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    os.chdir("/tmp/remake_subdir2")
    Rule(target="b", deps="aaa", builder=fooBuilder)
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
Rule(target="b", deps="a", builder=fooBuilder)
PatternRule(target="%.bar", deps="%.foo", builder=fooBuilder)
SubReMakeDir("/tmp/remake_subdir")
del fooBuilder
"""
    subReMakeFile = """
Rule(target="c", deps="../b", builder=fooBuilder)
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
    Rule(target="b", deps="a", builder=fooBuilder)
    PatternRule(target="%.bar", deps="%.foo", builder=fooBuilder)
    os.chdir("/tmp/remake_subdir")
    Rule(target="c", deps="../b", builder=fooBuilder)
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
Rule(target="c", deps="/tmp/remake_subdir/b", builder=fooBuilder)
PatternRule(target="%.baz", deps="%.bar", builder=fooBuilder)
Target("c")
Target("c.baz")
del fooBuilder
"""
    subReMakeFile = """
Rule(target="b", deps="a", builder=fooBuilder)
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
    Rule(target="c", deps="/tmp/remake_subdir/b", builder=fooBuilder)
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


# Nettoyage des deps (make clean)
# Detection of newer dep to rebuild target (replace os.path.isfile by shouldRebuild function)
# Pas de cycles
# Prevent nettoyage des deps (NoClean(target))
# Environnement avec dossier cache et output
# Show dependency tree in terminal
# Rules are executed in the order of apparition (currently subremake executed first)