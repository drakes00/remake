#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to context."""

from ward import test

from remake import setVerbose, unsetVerbose, isVerbose
from remake import setDryRun, unsetDryRun, isDryRun
from remake import setDevTest, unsetDevTest, isDevTest
from remake import setClean, unsetClean, isClean


@test("setVerbose sets VERBOSE to True")
def test_01_setVerbose():
    setVerbose()
    assert isVerbose() is True


@test("unsetVerbose sets VERBOSE to False")
def test_02_unsetVerbose():
    unsetVerbose()
    assert isVerbose() is False


@test("setDryRun sets DRY_RUN to True")
def test_03_setDryRun():
    setDryRun()
    assert isDryRun() is True


@test("unsetDryRun sets DRY_RUN to False")
def test_04_unsetDryRun():
    unsetDryRun()
    assert isDryRun() is False


@test("setDevTest sets DEV_TEST to True")
def test_05_setDevTest():
    setDevTest()
    assert isDevTest() is True


@test("unsetDevTest sets DEV_TEST to False")
def test_06_unsetDevTest():
    unsetDevTest()
    assert isDevTest() is False


@test("setClean sets CLEAN to True")
def test_07_setClean():
    setClean()
    assert isClean() is True


@test("unsetClean sets CLEAN to False")
def test_08_unsetClean():
    unsetClean()
    assert isClean() is False
