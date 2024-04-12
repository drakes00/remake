#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to context."""

import pathlib

from ward import test

from remake import setVerbose, unsetVerbose, isVerbose
from remake import setDryRun, unsetDryRun, isDryRun
from remake import setDevTest, unsetDevTest, isDevTest
from remake import setClean, unsetClean, isClean
from remake.context import getCurrentContext
from remake.main import AddTarget, AddVirtualTarget
from remake.paths import VirtualTarget


@test("setVerbose sets VERBOSE to True")
def test_01_setVerbose():
    """setVerbose sets VERBOSE to True"""
    setVerbose()
    assert isVerbose() is True


@test("unsetVerbose sets VERBOSE to False")
def test_02_unsetVerbose():
    """unsetVerbose sets VERBOSE to False"""
    unsetVerbose()
    assert isVerbose() is False


@test("setDryRun sets DRY_RUN to True")
def test_03_setDryRun():
    """setDryRun sets DRY_RUN to True"""
    setDryRun()
    assert isDryRun() is True


@test("unsetDryRun sets DRY_RUN to False")
def test_04_unsetDryRun():
    """unsetDryRun sets DRY_RUN to False"""
    unsetDryRun()
    assert isDryRun() is False


@test("setDevTest sets DEV_TEST to True")
def test_05_setDevTest():
    """setDevTest sets DEV_TEST to True"""
    setDevTest()
    assert isDevTest() is True


@test("unsetDevTest sets DEV_TEST to False")
def test_06_unsetDevTest():
    """unsetDevTest sets DEV_TEST to False"""
    unsetDevTest()
    assert isDevTest() is False


@test("setClean sets CLEAN to True")
def test_07_setClean():
    """setClean sets CLEAN to True"""
    setClean()
    assert isClean() is True


@test("unsetClean sets CLEAN to False")
def test_08_unsetClean():
    """unsetClean sets CLEAN to False"""
    unsetClean()
    assert isClean() is False


@test("AddTarget adds targets")
def test_09_addTarget():
    """AddTarget adds targets"""
    # One target.
    AddTarget("a")
    assert getCurrentContext().targets == [pathlib.Path(_).absolute() for _ in ("a")]
    getCurrentContext().clearTargets()

    # Multiple targets.
    AddTarget(["a", "b", "c"])
    assert getCurrentContext().targets == [pathlib.Path(_).absolute() for _ in ("a", "b", "c")]
    getCurrentContext().clearTargets()

    # One virtual target.
    AddVirtualTarget("a")
    assert getCurrentContext().targets == [VirtualTarget(_) for _ in ("a")]
    getCurrentContext().clearTargets()
