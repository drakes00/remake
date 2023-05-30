#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ward import test, raises

from remake import Builder, Rule, findBuildPath, clearRules

TMP_FILE = "/tmp/remake.tmp"




@test("Automatically detect dependencies")
def test_01_funDeps():
    """Automatically detect dependencies"""
    fooBuilder = Builder(action="")

    # One file one dependence.
    Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {"a": ["b"]}
    clearRules()

    # Two files one dependence.
    Rule(target="a", deps="c", builder=fooBuilder)
    Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {"a": ["c"]}
    assert findBuildPath("b") == {"b": ["c"]}
    clearRules()

    # One file two dependencies
    Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    assert findBuildPath("a") == {"a": ["b", "c"]}
    clearRules()

    # One file two dependencies
    Rule(target="a", deps="b", builder=fooBuilder)
    Rule(target="a", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {"a": ["b", "c"]}
    clearRules()

    # Three levels
    Rule(target="a", deps="b", builder=fooBuilder)
    Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {"a": [{"b": ["c"]}]}
    clearRules()

    # Complex
    Rule(target="d", deps=["c", "a2", "b1"], builder=fooBuilder)
    Rule(target="c", deps=["b1", "b2"], builder=fooBuilder)
    Rule(target="b1", deps=["a1"], builder=fooBuilder)
    Rule(target="b2", deps=["a1", "a2"], builder=fooBuilder)
    assert findBuildPath("d") == {'d': [{'c': [{'b1': ['a1']}, {'b2': ['a1', 'a2']}]}, 'a2', {'b1': ['a1']}]}
    clearRules()


@test("Dependency can appear multiple times in the tree")
def test_02_funDepsMultipleTimes():
    """Dependency can appear multiple times in the tree"""
    fooBuilder = Builder(action="")

    Rule(target="a", deps=["b", "c"], builder=fooBuilder)
    Rule(target="b", deps="c", builder=fooBuilder)
    assert findBuildPath("a") == {"a": [{"b": ["c"]}, "c"]}
    clearRules()

@test("Same rule applied twice should be ignored")
def test_03_funSameRuleTwice():
    """Same rule applied twice should be ignored"""
    fooBuilder = Builder(action="")

    # One file one dependence.
    Rule(target="a", deps="b", builder=fooBuilder)
    Rule(target="a", deps="b", builder=fooBuilder)
    assert findBuildPath("a") == {"a": ["b"]}
    clearRules()

@test("Rules must make target")
def test_04_funMakeTarget():
    """Rules must make target"""
    fooBuilder = Builder(action="ls > /dev/null")
    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # Ensure rule not making the target file will throw.
    rule = Rule(target=f"{TMP_FILE}", deps="", builder=fooBuilder)
    with raises(FileNotFoundError):
        rule.apply()
    clearRules()

    rule = Rule(target=f"{TMP_FILE}", deps="", builder=touchBuilder)
    rule.apply()
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)
    
# Pas de cycles
# Nettoyage des deps (make clean)
# Environnement avec dossier cache et output

