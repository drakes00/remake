#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from ward import test, fixture

from remake import Builder, Rule, PatternRule, getCurrentContext
from remake import unsetDryRun, unsetDevTest

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureCleanContext():
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


@test("Named rule deps can be a string of a list of string")
def test_03_deps(_=ensureCleanContext):
    """Named rule deps can be a string of a list of string"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $^")

    rule = Rule(targets="/tmp/bar", deps="/tmp/foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.targets == ["/tmp/bar"]

    rule2 = Rule(targets="/tmp/baz", deps=["/tmp/foo", "/tmp/bar"], builder=fooBuilder)
    assert rule2.deps == ["/tmp/foo", "/tmp/bar"]
    assert rule2.targets == ["/tmp/baz"]


@test("Named rule targets can be a string of a list of string")
def test_04_targets(_=ensureCleanContext):
    """Named rule targets can be a string of a list of string"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $^")

    rule = Rule(targets="/tmp/bar", deps="/tmp/foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.targets == ["/tmp/bar"]

    rule2 = Rule(targets=["/tmp/bar", "/tmp/baz"], deps="/tmp/foo", builder=fooBuilder)
    assert rule2.deps == ["/tmp/foo"]
    assert rule2.targets == ["/tmp/bar", "/tmp/baz"]


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
