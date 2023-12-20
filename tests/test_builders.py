#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to builders."""

import os
from ward import test, fixture

from remake import Builder, Rule, VirtualDep, VirtualTarget
from remake import getCurrentContext

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
    def check_foobar(deps, targets, _):
        assert isinstance(deps, list)
        assert isinstance(targets, list)
        assert deps == [VirtualDep(TMP_FILE)]
        assert targets == [VirtualTarget(TMP_FILE)]

    builder = Builder(action=check_foobar)
    rule = Rule(targets=VirtualTarget(TMP_FILE), deps=VirtualDep(TMP_FILE), builder=builder)
    rule.apply(None)
    getCurrentContext().clearRules()


@test("Builders can handle shell commands")
def test_02_builderShell(_=checkTmpFile):
    """Builders can handle shell commands"""

    builder = Builder(action=f"touch {TMP_FILE}")
    rule = Rule(targets=TMP_FILE, deps=[], builder=builder)
    rule.apply(None)
    getCurrentContext().clearRules()


@test("Builders can handle automatic variables ($^, $@)")
def test_03_builderAutoVar():
    """Builders can handle automatic variables ($^, $@)"""

    builder = Builder(action="cp $^ $@")
    rule = Rule(targets=TMP_FILE, deps=TMP_FILE, builder=builder)
    assert rule.action == f"cp {TMP_FILE} {TMP_FILE}"
    getCurrentContext().clearRules()


@test("Builders can handle kwargs.")
def test_04_buildersKwargs():
    """Builders can handle kwargs."""
    def check_foobar(deps, targets, _, myArg=None):
        assert isinstance(deps, list)
        assert isinstance(targets, list)
        assert deps in ([VirtualDep("/No Arg")], [VirtualDep("/With Arg")])
        assert targets in ([VirtualTarget("/No Arg")], [VirtualTarget("/With Arg")])
        if targets == [VirtualTarget("/No Arg")]:
            assert myArg is None
        elif targets == [VirtualTarget("/With Arg")]:
            assert myArg == "Cool"

    builder = Builder(action=check_foobar)
    r_1 = Rule(targets=VirtualTarget("/No Arg"), deps=VirtualDep("/No Arg"), builder=builder)
    r_2 = Rule(targets=VirtualTarget("/With Arg"), deps=VirtualDep("/With Arg"), myArg="Cool", builder=builder)
    r_1.apply(None)
    r_2.apply(None)
    getCurrentContext().clearRules()
