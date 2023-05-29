#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ward import test

from remake import Builder, Rule, PatternRule

TMP_FILE = "/tmp/remake.tmp"


@test("Rules can be named")
def test_01_namedRules():
    """Rules can be named"""

    builder = Builder(action=f"cp $^ $@")
    rule = Rule(target=TMP_FILE, deps=TMP_FILE, builder=builder)
    assert rule.deps == [TMP_FILE]
    assert rule.target == TMP_FILE


@test("Rules can be patterns")
def test_01_patternRules():
    """Rules can be patterns"""

    builder = Builder(action=f"cp $^ $@")
    rule = PatternRule(target="%.foo", deps="%.bar", builder=builder)
    assert rule.deps == ["%.bar"]
    assert rule.target == "%.foo"
