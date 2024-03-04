#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to builders."""

import os
import shutil
from pathlib import Path

from ward import test, fixture, raises, xfail

from remake import Builder, Rule, VirtualDep, VirtualTarget
from remake import getCurrentContext
from remake.builders import cp, mv, rm, tar

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


@fixture
def setupTestCopy():
    # Create some test files and directories
    os.makedirs("/tmp/remake", exist_ok=True)
    os.chdir("/tmp/remake")
    test_file_1 = "test_file_1.txt"
    test_file_2 = "test_file_2.txt"
    test_dir_1 = "test_dir_1"
    test_dir_2 = "test_dir_2"
    test_dir_3 = "test_dir_3"
    test_file_3 = test_dir_1 + "/test_file_3.txt"
    link_to_file_1 = "link_to_file_1.lnk"
    link_to_file_3 = "link_to_file_3.lnk"
    os.makedirs(test_dir_1, exist_ok=True)
    os.makedirs(test_dir_2, exist_ok=True)
    os.makedirs(test_dir_3, exist_ok=True)
    with open(test_file_1, "w") as f:
        f.write("This is a test file.")
    with open(test_file_2, "w") as f:
        f.write("Another test file.")
    with open(test_file_3, "w") as f:
        f.write("Another test file.")
    os.symlink(test_file_1, link_to_file_1)
    os.symlink(test_file_3, link_to_file_3)

    yield

    # Clean up test files and directories
    os.remove(test_file_1)
    os.remove(test_file_2)
    os.remove(test_file_3)
    os.remove(link_to_file_1)
    os.remove(link_to_file_3)
    shutil.rmtree(test_dir_1)
    shutil.rmtree(test_dir_2)
    shutil.rmtree(test_dir_3)


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
    rule.apply()
    getCurrentContext().clearRules()


@test("Builders can handle shell commands")
def test_02_builderShell(_=checkTmpFile):
    """Builders can handle shell commands"""

    builder = Builder(action=f"touch {TMP_FILE}")
    rule = Rule(targets=TMP_FILE, deps=[], builder=builder)
    rule.apply()
    getCurrentContext().clearRules()


@test("Builders can handle automatic variables ($^, $@)")
def test_03_builderAutoVar():
    """Builders can handle automatic variables ($^, $@)"""

    builder = Builder(action="cp $^ $@")
    rule = Rule(targets=TMP_FILE, deps=TMP_FILE, builder=builder)
    assert rule.actionName == f"cp {TMP_FILE} {TMP_FILE}"
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
    r_1.apply()
    r_2.apply()
    getCurrentContext().clearRules()


@test("Basic copy operations.")
def test_05_copyFileOperations(_=setupTestCopy):
    """Basic copy operations."""
    def _doCopy(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=cp).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_file_2 = Path("test_file_2.txt")
    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")
    test_dir_3 = Path("test_dir_3")
    test_file_3 = test_dir_1 / "test_file_3.txt"
    link_to_file_1 = Path("link_to_file_1.lnk")
    link_to_file_3 = Path("link_to_file_3.lnk")

    # Single file
    source = test_file_1
    destination = test_dir_1 / "copied_file.txt"
    _doCopy(source, destination)
    assert destination.exists() is True
    with open(destination, "r") as f:
        content = f.read()
    assert content == "This is a test file."
    os.remove(destination)

    # Multiple files
    sources = [test_file_1, test_file_2]
    destination_dir = test_dir_2
    _doCopy(sources, destination_dir)
    for source in sources:
        filename = os.path.basename(source)
        destination = destination_dir / filename
        assert destination.exists() is True
        os.remove(destination)

    # Non-existant source file
    source = "nonexistent_file.txt"
    destination = test_dir_1 / "copied_file.txt"
    with raises(FileNotFoundError):
        _doCopy(source, destination)

    # Non-existent destination directory
    source = test_file_1
    destination = "nonexistent_dir/copied_file.txt"
    with raises(OSError):
        _doCopy(source, destination)

    # Single directory
    source = test_dir_1
    destination_dir = test_dir_3 / "copied_dir"
    destination_file = destination_dir / test_file_3
    _doCopy(source, destination_dir)
    assert destination_file.exists() is True
    assert destination_file.is_file() is True
    assert destination_dir.exists() is True
    assert destination_dir.is_dir() is True
    shutil.rmtree(destination_dir)

    # Multiple directories
    sources = [test_dir_1, test_dir_2]
    destination_dir = test_dir_3 / "copied_dirs"
    destination_file = destination_dir / test_file_3
    # destination_file = test_file_3.replace("test_dir_1", destination_dir)
    _doCopy(sources, destination_dir)
    assert destination_file.exists() is True
    assert destination_file.is_file() is True
    assert (destination_dir / sources[0]).exists() is True
    assert (destination_dir / sources[0]).is_dir() is True
    assert (destination_dir / sources[1]).exists() is True
    assert (destination_dir / sources[1]).is_dir() is True
    shutil.rmtree(destination_dir)

    # Non-existent source directory
    source = "nonexistent_dir"
    destination = test_dir_2 / "copied_dir"
    with raises(FileNotFoundError):
        _doCopy(source, destination)

    # Non-existent destination directory for directory
    # OK: Will work since shutil.copytree will create intermediate directories.
    # Thus same as aabove.

    # IMPORTANT: Links are automatically resolved during rule process!
    # Single link
    source = link_to_file_1
    destination = test_dir_1 / "copied_link.lnk"
    _doCopy(source, destination)
    assert destination.exists() is True
    assert destination.is_file() is True
    with open(destination, "r") as f:
        content = f.read()
    assert content == "This is a test file."
    os.remove(destination)

    # Multiple links
    sources = [link_to_file_1, link_to_file_3]
    destination_dir = test_dir_2
    _doCopy(sources, destination_dir)
    for source in sources:
        destination = destination_dir / source.resolve().name
        assert destination.exists() is True
        assert destination.is_file() is True
        os.remove(destination)

    # Non-existent source link
    source = "nonexistent_link.lnk"
    destination = test_dir_1 / "copied_link.lnk"
    with raises(FileNotFoundError):
        _doCopy(source, destination)

    # Non-existent destination directory for link
    source = link_to_file_1
    destination = "nonexistent_dir/copied_link.lnk"
    with raises(FileNotFoundError):
        _doCopy(source, destination)


@test("Basic move operations.")
@xfail
def test_06_moveFileOperations():
    """Basic move operations."""
    raise NotImplementedError
    # === Move ===
    # Files (single, multiple, non-existant source, non-existant dest)
    # Directorie (single, multiple, non-existant source, non-existant dest)
    # Links (single, multiple, non-existant source, non-existant dest)


@test("Basic remove operations.")
@xfail
def test_07_removeFileOperations():
    """Basic remove operations."""
    raise NotImplementedError
    # === Remove ===
    # Files (single, multiple, non-existant)
    # Directorie (single, multiple, non-existant, not empty)
