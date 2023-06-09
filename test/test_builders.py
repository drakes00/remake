#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ward import test, fixture, raises

from remake import Builder, Rule, getCurrentContext

TMP_FILE = "/tmp/remake.tmp"


@fixture
def checkTmpFile():
    """Check for temp file creation"""
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    yield
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)


@test("Builders can handle python functions")
def test_01_builderPyFun():
    """Builders can handle python functions"""

    def check_foobar(deps, target):
        assert isinstance(deps, list)
        assert isinstance(target, str)
        assert deps == ["bar"]
        assert target == "foo"

    builder = Builder(action=check_foobar)
    rule = Rule(target="foo", deps="bar", builder=builder)
    with raises(FileNotFoundError):
        rule.apply()
    getCurrentContext().clearRules()


@test("Builders can handle shell commands")
def test_02_builderShell(_=checkTmpFile):
    """Builders can handle shell commands"""

    builder = Builder(action=f"touch {TMP_FILE}")
    rule = Rule(target=TMP_FILE, deps=[], builder=builder)
    rule.apply()
    getCurrentContext().clearRules()


@test("Builders can handle automatic variables ($^, $@)")
def test_03_builderAutoVar():
    """Builders can handle automatic variables ($^, $@)"""

    builder = Builder(action="cp $^ $@")
    rule = Rule(target=TMP_FILE, deps=TMP_FILE, builder=builder)
    assert rule.action == f"cp {TMP_FILE} {TMP_FILE}"
    getCurrentContext().clearRules()


# Présence de builders avec fonctions natives (déplacer, supprimer, etc)
# Bibliothèque de builders de base (C, Latex, etc)
