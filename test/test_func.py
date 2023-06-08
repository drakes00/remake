#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from ward import test, raises, fixture

from remake import Builder, Rule, PatternRule, Target
from remake import findBuildPath, clearRules, getRules, clearTargets, getTargets, loadScript

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureEmptyRuleList():
    clearRules()
    yield
    clearRules()


@fixture
def ensureEmptyTmp():
    try:
        os.remove("/tmp/ReMakeFile")
        shutil.rmtree("/tmp/remake_subdir")
    except FileNotFoundError:
        pass

    yield

    #try:
    #    os.remove("/tmp/ReMakeFile")
    #    shutil.rmtree("/tmp/remake_subdir")
    #except FileNotFoundError:
    #    pass


@test("Automatically detect dependencies")
def test_01_funDeps(_=ensureEmptyRuleList):
    """Automatically detect dependencies"""
    fooBuilder = Builder(action="")

    # One file one dependence.
    r_1 = Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_1): ["b"]}
    clearRules()

    # Two files one dependence.
    r_2_1 = Rule(target="a", deps="c", builder=fooBuilder)
    r_2_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_2_1): ["c"]}
    assert findBuildPath("b") == {("b", r_2_2): ["c"]}
    clearRules()

    # One file two dependencies
    r_3_1 = Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_3_1): ["b", "c"]}
    clearRules()

    # One file two dependencies with two rules.
    #FIXME Detect ambigous build paths!
    #r_4_1 = Rule(target="a", deps="b", builder=fooBuilder)
    #r_4_2 = Rule(target="a", deps="c", builder=fooBuilder)
    #assert findBuildPath("a") == {("a": ["b", "c"]}
    #clearRules()

    # Three levels
    r_5_1 = Rule(target="a", deps="b", builder=fooBuilder)
    r_5_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_5_1): [{("b", r_5_2): ["c"]}]}
    clearRules()

    # Complex
    r_6_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_6_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_6_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_6_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    assert findBuildPath("d") == {("d", r_6_1): [{("c", r_6_2): [{("b1", r_6_3): ["a1"]}, {("b2", r_6_4): ["a1", "a2"]}]}, "a2", {("b1", r_6_3): ["a1"]}]}


@test("Dependency can appear multiple times in the tree")
def test_02_funDepsMultipleTimes(_=ensureEmptyRuleList):
    """Dependency can appear multiple times in the tree"""
    fooBuilder = Builder(action="")

    r_1 = Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    r_2 = Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_1): [{("b", r_2): ["c"]}, "c"]}


@test("Same rule applied twice should be ignored")
def test_03_funSameRuleTwice(_=ensureEmptyRuleList):
    """Same rule applied twice should be ignored"""
    fooBuilder = Builder(action="")

    # One file one dependence.
    r_1 = Rule(target="a", deps="b", builder=fooBuilder)
    r_2 = Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {("a", r_1): ["b"]}


@test("Rules must make target")
def test_04_funMakeTarget(_=ensureEmptyRuleList):
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
        rule.apply()
    clearRules()

    rule = Rule(target=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    rule.apply()
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)


@test("ReMakeFile can be parsed")
def test_05_parseReMakeFile(_=ensureEmptyRuleList):
    """ReMakeFile can be parsed"""
    ReMakeFile = """
fooBuilder = Builder(action="")
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
    loadScript()
    named, pattern = getRules()
    targets = getTargets()
    clearRules()
    clearTargets()

    fooBuilder = Builder(action="")
    r_1 = Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    r_2 = Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    r_3 = Rule(target="b1", deps=["a1"], builder=fooBuilder)
    r_4 = Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    r_5 = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    Target("d")
    Target("d.foo")

    assert all([named[i] == [r_1, r_2, r_3, r_4][i] for i in range(len(named))])
    assert pattern == [r_5]
    assert targets == ["d", "d.foo"]


@test("Sub ReMakeFiles can be called.")
def test_06_parseSubReMakeFile(_=ensureEmptyRuleList, _2=ensureEmptyTmp):
    """Sub ReMakeFiles can be called."""
    ReMakeFile = f"""
SubReMakeDir("/tmp/remake_subdir")
"""
    subReMakeFile = """
fooBuilder = Builder(action="touch $@")
Rule(target="foo", deps=[], builder=fooBuilder)
Target("foo")
"""
    with open("/tmp/ReMakeFile", "w+") as handle:
        handle.write(ReMakeFile)

    os.mkdir("/tmp/remake_subdir")
    with open("/tmp/remake_subdir/ReMakeFile", "w+") as handle:
        handle.write(subReMakeFile)
    
    os.chdir("/tmp")
    loadScript()
    assert os.path.isfile("/tmp/remake_subdir/foo")


# Pas de cycles
# Nettoyage des deps (make clean)
# Prevent nettoyage des deps (NoClean(target))
# Environnement avec dossier cache et output
