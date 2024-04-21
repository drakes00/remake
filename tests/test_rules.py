#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to rules."""

import os
import pathlib

from typeguard import TypeCheckError
from ward import test, fixture, raises, xfail

from remake import Builder, Rule, PatternRule, VirtualDep, VirtualTarget, GlobPattern
from remake import unsetDryRun, unsetDevTest, getCurrentContext


@fixture
def ensureCleanContext():
    """Fixture clearing context before and after testcase."""
    getCurrentContext().clearRules()
    yield
    getCurrentContext().clearRules()
    unsetDryRun()
    unsetDevTest()


@test("Named rules can accept absolute paths")
def test_01_namedRulesAbsolutePath(_=ensureCleanContext):
    """Named rules can accept absolute paths"""

    os.chdir("/etc")  # Using a different directory than paths in rules.
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Absolute paths as string.
    r_1 = Rule(targets="/tmp/a", deps="/tmp/b", builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b")]
    assert r_1.targets == [pathlib.Path("/tmp/a")]

    # Pathlib absolute paths as string.
    r_2 = Rule(targets=pathlib.Path("/tmp/a"), deps=pathlib.Path("/tmp/b"), builder=fooBuilder)
    assert r_2.deps == [pathlib.Path("/tmp/b")]
    assert r_2.targets == [pathlib.Path("/tmp/a")]

    # Virtual absolute paths as string.
    r_3 = Rule(targets=VirtualTarget("/tmp/a"), deps=VirtualDep("/tmp/b"), builder=fooBuilder)
    assert r_3.deps == [VirtualDep("/tmp/b")]
    assert r_3.targets == [VirtualTarget("/tmp/a")]


@test("Named rules can accept relative paths")
def test_02_namedRulesRelativePath(_=ensureCleanContext):
    """Named rules can accept relative paths"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Relative paths as string.
    r_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    assert r_1.deps == [pathlib.Path("/tmp/b")]
    assert r_1.targets == [pathlib.Path("/tmp/a")]

    # Pathlib relative paths as string.
    r_2 = Rule(targets=pathlib.Path("a"), deps=pathlib.Path("b"), builder=fooBuilder)
    assert r_2.deps == [pathlib.Path("/tmp/b")]
    assert r_2.targets == [pathlib.Path("/tmp/a")]

    # Virtual relative paths as string are NOT expanded.
    r_3 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert r_3.deps == [VirtualDep("b")]
    assert r_3.targets == [VirtualTarget("a")]

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


@test("Pattern rules can expand to named targets")
def test_06_patternRulesMatchExpand(_=ensureCleanContext):
    """Pattern rules can expand to named targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder)
    assert rule.match("a.foo") == [pathlib.Path("a.bar")]
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []

    # Multiple deps pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps=["*.bar", "*.baz"], builder=fooBuilder)
    assert rule.match("a.foo") == [pathlib.Path("a.bar"), pathlib.Path("a.baz")]
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []

    # Simple pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps="test_*", builder=fooBuilder)
    assert rule.match("tmp_a") == [pathlib.Path("test_a")]
    assert rule.match("test_a") == []
    assert rule.match("tmp_b") == [pathlib.Path("test_b")]

    # Multiple deps pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps=["test_*", "data_*"], builder=fooBuilder)
    assert rule.match("tmp_a") == [pathlib.Path("test_a"), pathlib.Path("data_a")]
    assert rule.match("test_a") == []
    assert rule.match("tmp_b") == [pathlib.Path("test_b"), pathlib.Path("data_b")]

    # Simple pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps="test_*.bar", builder=fooBuilder)
    assert rule.match("tmp_a.foo") == [pathlib.Path("test_a.bar")]
    assert rule.match("tmp_a.bar") == []
    assert rule.match("tmp_a.baz") == []

    # Multiple deps pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps=["test_*.bar", "test_*.baz"], builder=fooBuilder)
    assert rule.match("tmp_a.foo") == [pathlib.Path("test_a.bar"), pathlib.Path("test_a.baz")]
    assert rule.match("tmp_a.bar") == []
    assert rule.match("tmp_a.baz") == []


@test("Pattern rules can exlude targets")
def test_07_patternRulesExcludeTargets(_=ensureCleanContext):
    """Pattern rules can exlude targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps="*.bar", builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == []
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []
    assert rule.match("b.foo") == [pathlib.Path("b.bar")]
    assert rule.match("b.bar") == []
    assert rule.match("b.baz") == []

    # Multiple deps pattern rule with fixed RHS.
    rule = PatternRule(target="*.foo", deps=["*.bar", "*.baz"], builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == []
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []
    assert rule.match("b.foo") == [pathlib.Path("b.bar"), pathlib.Path("b.baz")]
    assert rule.match("b.bar") == []
    assert rule.match("b.baz") == []

    # Simple pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps="test_*", builder=fooBuilder, exclude=["tmp_a"])
    assert rule.match("tmp_a") == []
    assert rule.match("test_a") == []
    assert rule.match("main_a") == []
    assert rule.match("tmp_b") == [pathlib.Path("test_b")]
    assert rule.match("test_b") == []
    assert rule.match("main_b") == []

    # Multiple deps pattern rule with fixed LHS.
    rule = PatternRule(target="tmp_*", deps=["test_*", "data_*"], builder=fooBuilder, exclude=["tmp_a"])
    assert rule.match("tmp_a") == []
    assert rule.match("test_a") == []
    assert rule.match("main_a") == []
    assert rule.match("tmp_b") == [pathlib.Path("test_b"), pathlib.Path("data_b")]
    assert rule.match("test_b") == []
    assert rule.match("main_b") == []

    # Simple pattern rule with both fixed LHS and RHS.
    rule = PatternRule(target="tmp_*.foo", deps="test_*.bar", builder=fooBuilder, exclude=["tmp_a.foo"])
    assert rule.match("tmp_a.foo") == []
    assert rule.match("test_a.bar") == []
    assert rule.match("tmp_a.baz") == []
    assert rule.match("test_a.baz") == []
    assert rule.match("tmp_b.foo") == [pathlib.Path("test_b.bar")]
    assert rule.match("test_b.bar") == []
    assert rule.match("tmp_b.baz") == []
    assert rule.match("test_b.baz") == []

    # Multiple deps pattern rule with both fixed LHS and RHS.
    rule = PatternRule(
        target="tmp_*.foo",
        deps=["test_*.bar",
              "data_*.baz"],
        builder=fooBuilder,
        exclude=["tmp_a.foo"],
    )
    assert rule.match("tmp_a.foo") == []
    assert rule.match("test_a.bar") == []
    assert rule.match("tmp_a.baz") == []
    assert rule.match("test_a.foo") == []
    assert rule.match("tmp_b.foo") == [pathlib.Path("test_b.bar"), pathlib.Path("data_b.baz")]
    assert rule.match("test_b.bar") == []
    assert rule.match("tmp_b.baz") == []
    assert rule.match("test_b.foo") == []


#     # Paths with ../ (all)
