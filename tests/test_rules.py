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

    fooBuilder = Builder(action="Magically creating $@ from $<")
    rule = Rule(target=TMP_FILE, deps=TMP_FILE, builder=fooBuilder)
    assert rule.deps == [TMP_FILE]
    assert rule.target == TMP_FILE


@test("Rules can be patterns")
def test_01_patternRules(_=ensureCleanContext):
    """Rules can be patterns"""

    fooBuilder = Builder(action="Magically creating $@ from $<")
    rule = PatternRule(target="%.foo", deps="%.bar", builder=fooBuilder)
    assert rule.deps == ["%.bar"]
    assert rule.target == "%.foo"


@test("Named rule deps can be a string of a list of string")
def test_03_deps(_=ensureCleanContext):
    """Named rule deps can be a string of a list of string"""

    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")

    rule = Rule(target="/tmp/bar", deps="/tmp/foo", builder=fooBuilder)
    assert rule.deps == ["/tmp/foo"]
    assert rule.target == "/tmp/bar"

    rule2 = Rule(target="/tmp/baz", deps=["/tmp/foo", "/tmp/bar"], builder=fooBuilder)
    assert rule2.deps == ["/tmp/foo", "/tmp/bar"]
    assert rule2.target == "/tmp/baz"


#@test("Named rule targets can be a string of a list of string")
#def test_04_targets(_=ensureCleanContext):
#    """Named rule targets can be a string of a list of string"""
#
#    os.chdir("/tmp")
#    fooBuilder = Builder(action="Magically creating $@ from $<")
#
#    rule = Rule(target="/tmp/bar", deps="/tmp/foo", builder=fooBuilder)
#    assert rule.deps == ["/tmp/foo"]
#    assert rule.target == ["/tmp/bar"]
#
#    rule2 = Rule(target="/tmp/baz", deps=["/tmp/foo", "/tmp/bar"], builder=fooBuilder)
#    assert rule2.deps == ["/tmp/foo"]
#    assert rule2.target == ["/tmp/bar", "/tmp/baz"]