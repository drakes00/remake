#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to rules."""

import os
import pathlib

from typeguard import TypeCheckError
from ward import test, fixture, raises

from remake import Builder, Rule, PatternRule, VirtualDep, VirtualTarget, GlobPattern
from remake import unsetDryRun, unsetDevTest, getCurrentContext


@fixture
def ensureCleanContext():
    """Fixture clearing context before and after testcase."""

    # Save current directory.
    prev_dir = os.getcwd()

    getCurrentContext().clearRules()

    yield

    getCurrentContext().clearRules()
    unsetDryRun()
    unsetDevTest()

    # Restore previous directory.
    os.chdir(prev_dir)


@test("Named rules can accept absolute paths")
def test_01_namedRulesAbsolutePath(_=ensureCleanContext):
    """Named rules can accept absolute paths"""

    os.chdir("/etc")  # Using a different directory than paths in rules.
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Absolute paths as string.
    r_1 = Rule(targets="/tmp/a", deps="/tmp/b", builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b")]
    assert r_1.targets == [pathlib.Path("/tmp/a")]
    assert r_1.match("/tmp/a")
    assert not r_1.match("/tmp/b")

    # Pathlib absolute paths as string.
    r_2 = Rule(targets=pathlib.Path("/tmp/a"), deps=pathlib.Path("/tmp/b"), builder=fooBuilder)
    assert r_2.deps == [pathlib.Path("/tmp/b")]
    assert r_2.targets == [pathlib.Path("/tmp/a")]
    assert r_2.match(pathlib.Path("/tmp/a"))
    assert not r_2.match(pathlib.Path("/tmp/b"))

    # Virtual absolute paths as string.
    r_3 = Rule(targets=VirtualTarget("/tmp/a"), deps=VirtualDep("/tmp/b"), builder=fooBuilder)
    assert r_3.deps == [VirtualDep("/tmp/b")]
    assert r_3.targets == [VirtualTarget("/tmp/a")]
    assert r_3.match(VirtualTarget("/tmp/a"))
    assert not r_3.match(VirtualTarget("/tmp/b"))


@test("Named rules can accept relative paths")
def test_02_namedRulesRelativePath(_=ensureCleanContext):
    """Nampprintpped rules can accept relative paths"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Relative paths as string.
    r_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b")]
    assert r_1.targets == [pathlib.Path("/tmp/a")]
    assert r_1.match("/tmp/a")
    assert not r_1.match("/tmp/b")

    # Pathlib relative paths as string.
    r_2 = Rule(targets=pathlib.Path("a"), deps=pathlib.Path("b"), builder=fooBuilder)
    assert r_2.deps == [pathlib.Path("/tmp/b")]
    assert r_2.targets == [pathlib.Path("/tmp/a")]
    assert r_2.match(pathlib.Path("/tmp/a"))
    assert not r_2.match(pathlib.Path("/tmp/b"))

    # Virtual relative paths as string are NOT expanded.
    r_3 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert r_3.deps == [VirtualDep("b")]
    assert r_3.targets == [VirtualTarget("a")]
    assert r_3.match(VirtualTarget("a"))
    assert not r_3.match(VirtualTarget("b"))

    # Check VirtualTargets
    with raises(TypeCheckError):
        Rule(targets="bar", deps=VirtualTarget("foo"), builder=fooBuilder)

    # Check VirtualDeps
    with raises(TypeCheckError):
        Rule(targets=VirtualDep("bar"), deps="foo", builder=fooBuilder)


@test("Named rules can accept list of absolute paths")
def test_03_namedRulesListAbsolutePath(_=ensureCleanContext):
    """Named rules can accept list of absolute paths"""

    os.chdir("/etc")  # Using a different directory than paths in rules.
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # List of absolute paths as strings.
    r_1 = Rule(targets=["/tmp/a1", "/tmp/a2"], deps=["/tmp/b1", "/tmp/b2"], builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b1"), pathlib.Path("/tmp/b2")]
    assert r_1.targets == [pathlib.Path("/tmp/a1"), pathlib.Path("/tmp/a2")]

    # List of absolute paths as pathlib paths.
    r_2 = Rule(
        targets=[pathlib.Path("/tmp/a1"),
                 pathlib.Path("/tmp/a2")],
        deps=[pathlib.Path("/tmp/b1"),
              pathlib.Path("/tmp/b2")],
        builder=fooBuilder
    )
    assert r_2.deps == [pathlib.Path("/tmp/b1"), pathlib.Path("/tmp/b2")]
    assert r_2.targets == [pathlib.Path("/tmp/a1"), pathlib.Path("/tmp/a2")]

    # List of virtual absolute paths.
    r_3 = Rule(
        targets=[VirtualTarget("/tmp/a1"),
                 VirtualTarget("/tmp/a2")],
        deps=[VirtualDep("/tmp/b1"),
              VirtualDep("/tmp/b2")],
        builder=fooBuilder
    )
    assert r_3.deps == [VirtualDep("/tmp/b1"), VirtualDep("/tmp/b2")]
    assert r_3.targets == [VirtualTarget("/tmp/a1"), VirtualTarget("/tmp/a2")]


@test("Named rules can accept list of relative paths")
def test_04_namedRulesListRelativePath(_=ensureCleanContext):
    """Named rules can accept list of relative paths"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # List of absolute paths as strings.
    r_1 = Rule(targets=["a1", "a2"], deps=["b1", "b2"], builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b1"), pathlib.Path("/tmp/b2")]
    assert r_1.targets == [pathlib.Path("/tmp/a1"), pathlib.Path("/tmp/a2")]

    # List of absolute paths as pathlib paths.
    r_2 = Rule(
        targets=[pathlib.Path("a1"),
                 pathlib.Path("a2")],
        deps=[pathlib.Path("b1"),
              pathlib.Path("b2")],
        builder=fooBuilder
    )
    assert r_2.deps == [pathlib.Path("/tmp/b1"), pathlib.Path("/tmp/b2")]
    assert r_2.targets == [pathlib.Path("/tmp/a1"), pathlib.Path("/tmp/a2")]

    # Virtual relative paths as string are NOT expanded.
    r_3 = Rule(
        targets=[VirtualTarget("a1"),
                 VirtualTarget("a2")],
        deps=[VirtualDep("b1"),
              VirtualDep("b2")],
        builder=fooBuilder
    )
    assert r_3.deps == [VirtualDep("b1"), VirtualDep("b2")]
    assert r_3.targets == [VirtualTarget("a1"), VirtualTarget("a2")]

    # Check VirtualTargets
    with raises(TypeCheckError):
        Rule(targets="bar", deps=[VirtualTarget("foo"), VirtualTarget("foo2")], builder=fooBuilder)

    # Check VirtualDeps
    with raises(TypeCheckError):
        Rule(targets=[VirtualDep("bar"), VirtualDep("bar2")], deps="foo", builder=fooBuilder)


@test("Rules can be patterns")
def test_05_patternRules(_=ensureCleanContext):
    """Rules can be patterns"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Pattern rule with RHS fixed part.
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    assert rule.deps == [GlobPattern("*.bar")]
    assert rule.targets == [GlobPattern("*.foo")]

    # Pattern rule with LHS fixed part.
    rule = PatternRule(target="tmp_*", deps="test_*", builder=fooBuilder)
    assert rule.deps == [GlobPattern("test_*")]
    assert rule.targets == [GlobPattern("tmp_*")]

    # Pattern rule with both LHS and RHS fixed part.
    rule = PatternRule(target="main_*.foo", deps="main_*.bar", builder=fooBuilder)
    assert rule.deps == [GlobPattern("main_*.bar")]
    assert rule.targets == [GlobPattern("main_*.foo")]


@test("Pattern rules can be matched to named targets")
def test_06_patternRulesMatch(_=ensureCleanContext):
    """Pattern rules can be matched to named targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    assert rule.match("a.foo") == (pathlib.Path("a.foo"), [pathlib.Path("a.bar")])
    assert rule.match("a.bar") == (pathlib.Path("a.bar"), [])
    assert rule.match("a.baz") == (pathlib.Path("a.baz"), [])

    # Multiple deps pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps=["*.bar", "*.baz"], builder=fooBuilder)
    assert rule.match("a.foo") == (pathlib.Path("a.foo"), [pathlib.Path("a.bar"), pathlib.Path("a.baz")])
    assert rule.match("a.bar") == (pathlib.Path("a.bar"), [])
    assert rule.match("a.baz") == (pathlib.Path("a.baz"), [])

    # Simple pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps="test_*", builder=fooBuilder)
    assert rule.match("tmp_a") == (pathlib.Path("tmp_a"), [pathlib.Path("test_a")])
    assert rule.match("test_a") == (pathlib.Path("test_a"), [])
    assert rule.match("tmp_b") == (pathlib.Path("tmp_b"), [pathlib.Path("test_b")])

    # Multiple deps pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps=["test_*", "data_*"], builder=fooBuilder)
    assert rule.match("tmp_a") == (pathlib.Path("tmp_a"), [pathlib.Path("test_a"), pathlib.Path("data_a")])
    assert rule.match("test_a") == (pathlib.Path("test_a"), [])
    assert rule.match("tmp_b") == (pathlib.Path("tmp_b"), [pathlib.Path("test_b"), pathlib.Path("data_b")])

    # Simple pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps="test_*.bar", builder=fooBuilder)
    assert rule.match("tmp_a.foo") == (pathlib.Path("tmp_a.foo"), [pathlib.Path("test_a.bar")])
    assert rule.match("tmp_a.bar") == (pathlib.Path("tmp_a.bar"), [])
    assert rule.match("tmp_a.baz") == (pathlib.Path("tmp_a.baz"), [])

    # Multiple deps pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps=["test_*.bar", "test_*.baz"], builder=fooBuilder)
    assert rule.match("tmp_a.foo"
                     ) == (pathlib.Path("tmp_a.foo"),
                           [pathlib.Path("test_a.bar"),
                            pathlib.Path("test_a.baz")])
    assert rule.match("tmp_a.bar") == (pathlib.Path("tmp_a.bar"), [])
    assert rule.match("tmp_a.baz") == (pathlib.Path("tmp_a.baz"), [])


@test("Pattern rules can exlude targets")
def test_07_patternRulesExcludeTargets(_=ensureCleanContext):
    """Pattern rules can exlude targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == (pathlib.Path("a.foo"), [])
    assert rule.match("a.bar") == (pathlib.Path("a.bar"), [])
    assert rule.match("a.baz") == (pathlib.Path("a.baz"), [])
    assert rule.match("b.foo") == (pathlib.Path("b.foo"), [pathlib.Path("b.bar")])
    assert rule.match("b.bar") == (pathlib.Path("b.bar"), [])
    assert rule.match("b.baz") == (pathlib.Path("b.baz"), [])

    # Multiple deps pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps=["*.bar", "*.baz"], builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == (pathlib.Path("a.foo"), [])
    assert rule.match("a.bar") == (pathlib.Path("a.bar"), [])
    assert rule.match("a.baz") == (pathlib.Path("a.baz"), [])
    assert rule.match("b.foo") == (pathlib.Path("b.foo"), [pathlib.Path("b.bar"), pathlib.Path("b.baz")])
    assert rule.match("b.bar") == (pathlib.Path("b.bar"), [])
    assert rule.match("b.baz") == (pathlib.Path("b.baz"), [])

    # Simple pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps="test_*", builder=fooBuilder, exclude=["tmp_a"])
    assert rule.match("tmp_a") == (pathlib.Path("tmp_a"), [])
    assert rule.match("test_a") == (pathlib.Path("test_a"), [])
    assert rule.match("main_a") == (pathlib.Path("main_a"), [])
    assert rule.match("tmp_b") == (pathlib.Path("tmp_b"), [pathlib.Path("test_b")])
    assert rule.match("test_b") == (pathlib.Path("test_b"), [])
    assert rule.match("main_b") == (pathlib.Path("main_b"), [])

    # Multiple deps pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps=["test_*", "data_*"], builder=fooBuilder, exclude=["tmp_a"])
    assert rule.match("tmp_a") == (pathlib.Path("tmp_a"), [])
    assert rule.match("test_a") == (pathlib.Path("test_a"), [])
    assert rule.match("main_a") == (pathlib.Path("main_a"), [])
    assert rule.match("tmp_b") == (pathlib.Path("tmp_b"), [pathlib.Path("test_b"), pathlib.Path("data_b")])
    assert rule.match("test_b") == (pathlib.Path("test_b"), [])
    assert rule.match("main_b") == (pathlib.Path("main_b"), [])

    # Simple pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps="test_*.bar", builder=fooBuilder, exclude=["tmp_a.foo"])
    assert rule.match("tmp_a.foo") == (pathlib.Path("tmp_a.foo"), [])
    assert rule.match("test_a.bar") == (pathlib.Path("test_a.bar"), [])
    assert rule.match("tmp_a.baz") == (pathlib.Path("tmp_a.baz"), [])
    assert rule.match("test_a.baz") == (pathlib.Path("test_a.baz"), [])
    assert rule.match("tmp_b.foo") == (pathlib.Path("tmp_b.foo"), [pathlib.Path("test_b.bar")])
    assert rule.match("test_b.bar") == (pathlib.Path("test_b.bar"), [])
    assert rule.match("tmp_b.baz") == (pathlib.Path("tmp_b.baz"), [])
    assert rule.match("test_b.baz") == (pathlib.Path("test_b.baz"), [])

    # Multiple deps pattern rule with both fixed LHS and RHS.
    rule = PatternRule(
        target="tmp_*.foo",
        deps=["test_*.bar",
              "data_*.baz"],
        builder=fooBuilder,
        exclude=["tmp_a.foo"],
    )
    assert rule.match("tmp_a.foo") == (pathlib.Path("tmp_a.foo"), [])
    assert rule.match("test_a.bar") == (pathlib.Path("test_a.bar"), [])
    assert rule.match("tmp_a.baz") == (pathlib.Path("tmp_a.baz"), [])
    assert rule.match("test_a.foo") == (pathlib.Path("test_a.foo"), [])
    assert rule.match("tmp_b.foo"
                     ) == (pathlib.Path("tmp_b.foo"),
                           [pathlib.Path("test_b.bar"),
                            pathlib.Path("data_b.baz")])
    assert rule.match("test_b.bar") == (pathlib.Path("test_b.bar"), [])
    assert rule.match("tmp_b.baz") == (pathlib.Path("tmp_b.baz"), [])
    assert rule.match("test_b.foo") == (pathlib.Path("test_b.foo"), [])


@test("Pattern rules can be expanded to a named rule")
def test_08_patternRulesExpand(_=ensureCleanContext):
    """Pattern rules can be expanded to a named rule"""

    os.chdir("/tmp")

    fooBuilder = Builder(action="Magically creating $@ from $^")
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    namedRule = rule.expand(pathlib.Path("a.foo"))

    assert namedRule.deps == [pathlib.Path("/tmp/a.bar")]
    assert namedRule.targets == [pathlib.Path("/tmp/a.foo")]

    expectedAction = " ".join(fooBuilder.action).replace("$@", "/tmp/a.foo").replace("$^", "/tmp/a.bar").split(" ")
    assert namedRule.action == expectedAction

#     # Paths with ../ (all)
