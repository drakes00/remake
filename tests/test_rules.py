#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to rules."""

import os

from ward import test, fixture, raises

from remake import Builder, Rule, PatternRule, VirtualDep, VirtualTarget
from remake import unsetDryRun, unsetDevTest, getCurrentContext

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureCleanContext():
    """Fixture clearing context before and after testcase."""
    getCurrentContext().clearRules()
    yield
    getCurrentContext().clearRules()
    unsetDryRun()
    unsetDevTest()


@test("Rules can be named")
def test_01_namedRules(_=ensureCleanContext):
    """Rules can be named"""

    fooBuilder = Builder(action="Magically creating $@ from $^")
    rule = Rule(targets=TMP_FILE, deps=TMP_FILE, builder=fooBuilder)
    assert rule.deps == [TMP_FILE]
    assert rule.targets == [TMP_FILE]


@test("Rules can be patterns")
def test_02_patternRules(_=ensureCleanContext):
    """Rules can be patterns"""

    fooBuilder = Builder(action="Magically creating $@ from $^")
    rule = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    assert rule.deps == ["%.bar"]
    assert rule.targets == ["%.foo"]


@test("Named rule deps can be a string or a list of string")
def test_03_deps(_=ensureCleanContext):
    """Named rule deps can be a string or a list of string"""

    fooBuilder = Builder(action="Magically creating $@ from $^")
    os.chdir("/tmp")

    # Check absolute paths.
    rule = Rule(targets="/foo/bar", deps="/foo/baz", builder=fooBuilder)
    assert rule.deps == ["/foo/baz"]
    assert rule.targets == ["/foo/bar"]

    # Check path expansion.
    rule = Rule(targets="bar", deps="foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.targets == ["/tmp/bar"]

    # Check VirtualDeps
    rule = Rule(targets="bar", deps=VirtualDep("foo"), builder=fooBuilder)
    assert rule.deps == [VirtualDep("foo")]
    assert rule.targets == ["/tmp/bar"]

    # Check VirtualTargets
    with raises(TypeError):
        rule = Rule(targets="bar", deps=VirtualTarget("foo"), builder=fooBuilder)


@test("Named rule targets can be a string or a list of string")
def test_04_targets(_=ensureCleanContext):
    """Named rule targets can be a string or a list of string"""

    fooBuilder = Builder(action="Magically creating $@ from $^")
    os.chdir("/tmp")

    # Check absolute paths.
    rule = Rule(targets="/foo/bar", deps="/foo/baz", builder=fooBuilder)
    assert rule.deps == ["/foo/baz"]
    assert rule.targets == ["/foo/bar"]

    # Check path expansion.
    rule = Rule(targets="bar", deps="foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.targets == ["/tmp/bar"]

    # Check VirtualTargets
    rule = Rule(targets=VirtualTarget("bar"), deps="foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.targets == [VirtualTarget("bar")]

    # Check VirtualDeps
    with raises(TypeError):
        rule = Rule(targets=VirtualDep("bar"), deps="foo", builder=fooBuilder)


@test("Pattern rules can expand to named targets")
def test_05_patternRulesMatchExpand(_=ensureCleanContext):
    """Pattern rules can expand to named targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule.
    rule = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    assert rule.match("a.foo") == ["a.bar"]
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []

    # Multiple deps pattern rule.
    rule = PatternRule(target="%.foo", deps=["%.bar", "%.baz"], builder=fooBuilder)
    assert rule.match("a.foo") == ["a.bar", "a.baz"]
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []


@test("Pattern rules can exlude targets")
def test_06_patternRulesExcludeTargets(_=ensureCleanContext):
    """Pattern rules can exlude targets"""

    fooBuilder = Builder(action="Magically creating $@ from $^")

    # Simple pattern rule.
    rule = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == []
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []
    assert rule.match("b.foo") == ["b.bar"]
    assert rule.match("b.bar") == []
    assert rule.match("b.baz") == []

    # Multiple deps pattern rule.
    rule = PatternRule(target="%.foo", deps=["%.bar", "%.baz"], builder=fooBuilder, exclude=["a.foo"])
    assert rule.match("a.foo") == []
    assert rule.match("a.bar") == []
    assert rule.match("a.baz") == []
    assert rule.match("b.foo") == ["b.bar", "b.baz"]
    assert rule.match("b.bar") == []
    assert rule.match("b.baz") == []
