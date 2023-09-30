#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from ward import test, fixture

from remake import Builder, Rule, getCurrentContext, setDryRun, unsetDryRun

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
        assert deps == [TMP_FILE]
        assert targets == [TMP_FILE]

    setDryRun()
    builder = Builder(action=check_foobar)
    rule = Rule(targets=TMP_FILE, deps=TMP_FILE, builder=builder)
    rule.apply(None)
    getCurrentContext().clearRules()
    unsetDryRun()


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
        assert deps in (["/No Arg"], ["/With Arg"])
        assert targets in (["/No Arg"], ["/With Arg"])
        if targets == ["/No Arg"]:
            assert myArg is None
        elif targets == ["/With Arg"]:
            assert myArg == "Cool"

    setDryRun()
    builder = Builder(action=check_foobar)
    r_1 = Rule(targets="/No Arg", deps="/No Arg", builder=builder)
    r_2 = Rule(targets="/With Arg", deps="/With Arg", myArg="Cool", builder=builder)
    r_1.apply(None)
    r_2.apply(None)
    getCurrentContext().clearRules()
    unsetDryRun()
