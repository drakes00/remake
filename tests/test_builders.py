#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests related to builders."""

import os
import shutil
import tarfile
import time
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
def setupTestCopyMove():
    # Create some test files and directories
    os.makedirs("/tmp/remake", exist_ok=True)
    os.chdir("/tmp/remake")
    test_file_1 = "test_file_1.txt"
    test_file_2 = "test_file_2.txt"
    test_dir_1 = "test_dir_1"
    test_dir_2 = "test_dir_2"
    test_dir_3 = "test_dir_3"
    test_dir_4 = "test_dir_4"
    test_file_3 = test_dir_1 + "/test_file_3.txt"
    link_to_file_1 = "link_to_file_1.lnk"
    link_to_file_3 = "link_to_file_3.lnk"
    os.makedirs(test_dir_1, exist_ok=True)
    os.makedirs(test_dir_2, exist_ok=True)
    os.makedirs(test_dir_3, exist_ok=True)
    os.makedirs(test_dir_4, exist_ok=True)
    with open(test_file_1, "w") as f:
        f.write("This is a test file.")
    with open(test_file_2, "w") as f:
        f.write("Another test file.")
    with open(test_file_3, "w") as f:
        f.write("Another other test file.")

    try:
        os.symlink(test_file_1, link_to_file_1)
        os.symlink(test_file_3, link_to_file_3)
    except FileExistsError:
        pass

    yield

    # Clean up test files and directories
    if os.path.isfile(test_file_1):
        os.remove(test_file_1)
    if os.path.isfile(test_file_2):
        os.remove(test_file_2)
    if os.path.isfile(test_file_3):
        os.remove(test_file_3)
    if os.path.islink(link_to_file_1):
        os.remove(link_to_file_1)
    if os.path.islink(link_to_file_3):
        os.remove(link_to_file_3)
    if os.path.isdir(test_dir_1):
        shutil.rmtree(test_dir_1)
    if os.path.isdir(test_dir_2):
        shutil.rmtree(test_dir_2)
    if os.path.isdir(test_dir_3):
        shutil.rmtree(test_dir_3)
    if os.path.isdir(test_dir_4):
        shutil.rmtree(test_dir_4)


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


@test("Basic file copy operations.")
def test_05_copyFileOperations(_=setupTestCopyMove):
    """Basic file copy operations."""
    def _doCopy(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=cp).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_file_2 = Path("test_file_2.txt")
    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")

    # Single file
    source = test_file_1
    destination = test_dir_1
    _doCopy(source, destination)
    assert (destination / source).is_file() is True
    with open(destination / source, "r") as f:
        content = f.read()
    assert content == "This is a test file."
    os.remove(destination / source)

    # Single file with rename
    source = test_file_1
    destination = test_dir_1 / "copied_file.txt"
    _doCopy(source, destination)
    assert destination.exists() is True
    with open(destination, "r") as f:
        content = f.read()
    assert content == "This is a test file."
    os.remove(destination)

    # Single file with replace
    source = test_file_1
    destination = test_dir_1 / "renamed_file.txt"
    _doCopy(source, destination)
    source = test_file_2
    time.sleep(0.1)
    source.touch()
    _doCopy(source, destination)
    assert destination.exists() is True
    with open(destination, "r") as f:
        content = f.read()
    assert content == "Another test file."
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

    # Non-existent destination directory single file
    source = test_file_1
    destination = "nonexistent_dir/copied_file.txt"
    with raises(FileNotFoundError):
        _doCopy(source, destination)

    # Non-existent destination directory
    source = [test_file_1, test_file_2]
    destination = "nonexistent_dir"
    with raises(FileNotFoundError):
        _doCopy(source, destination)


@test("Basic directory copy operations.")
def test_06_copyDirectoryOperations(_=setupTestCopyMove):
    """Basic directory copy operations."""
    def _doCopy(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=cp).apply()
        getCurrentContext().clearRules()

    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")
    test_dir_3 = Path("test_dir_3")
    test_file_3 = test_dir_1 / "test_file_3.txt"

    # Single directory
    source = test_dir_1
    destination_dir = test_dir_3
    destination_file = destination_dir / test_file_3
    _doCopy(source, destination_dir)
    assert destination_file.exists() is True
    assert destination_file.is_file() is True
    assert (destination_dir / source).exists() is True
    assert (destination_dir / source).is_dir() is True
    shutil.rmtree(destination_dir / source)

    # Single directory with rename
    source = test_dir_1
    destination_dir = test_dir_3 / "renamed_dir"
    destination_file = destination_dir / test_file_3.name
    _doCopy(source, destination_dir)
    assert destination_file.exists() is True
    assert destination_file.is_file() is True
    assert destination_dir.exists() is True
    assert destination_dir.is_dir() is True
    shutil.rmtree(destination_dir)

    # Multiple directories
    sources = [test_dir_1, test_dir_2]
    destination_dir = test_dir_3
    destination_file = destination_dir / test_file_3
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

    # Non-existent destination directory
    # OK: Will work since shutil.copytree will create intermediate directories.
    # Thus same as above.


@test("Basic link copy operations.")
def test_07_copyLinkOperations(_=setupTestCopyMove):
    """Basic link copy operations."""
    def _doCopy(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=cp).apply()
        getCurrentContext().clearRules()

    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")
    link_to_file_1 = Path("link_to_file_1.lnk")
    link_to_file_3 = Path("link_to_file_3.lnk")

    # Link will we followed during copy (copying the
    # file pointed by the link and not the link itself).

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
        destination = destination_dir / source.name
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


@test("Basic file move operations.")
def test_08_moveFileOperations(_=setupTestCopyMove):
    """Basic file move operations."""
    def _doMove(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=mv).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_file_2 = Path("test_file_2.txt")
    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")
    test_file_3 = test_dir_1 / "test_file_3.txt"

    # Single file
    source = test_file_1
    destination = test_dir_1 / "moved_file.txt"
    _doMove(source, destination)
    assert source.exists() is False
    assert destination.exists() is True
    with open(destination, "r") as f:
        content = f.read()
    assert content == "This is a test file."
    os.remove(destination)

    # Multiple files
    sources = [test_file_2, test_file_3]
    destination_dir = test_dir_2
    _doMove(sources, destination_dir)
    for source in sources:
        filename = os.path.basename(source)
        destination = destination_dir / filename
        assert source.exists() is False
        assert destination.exists() is True
        os.remove(destination)

    # Non-existant source file
    source = "nonexistent_file.txt"
    destination = test_dir_1 / "moved_file.txt"
    with raises(FileNotFoundError):
        _doMove(source, destination)

    # Non-existent destination directory
    source = test_file_1
    destination = "nonexistent_dir/moved_file.txt"
    with raises(OSError):
        _doMove(source, destination)


@test("Basic directory move operations.")
def test_09_moveDirectoryOperations(_=setupTestCopyMove):
    """Basic directory move operations."""
    def _doMove(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=mv).apply()
        getCurrentContext().clearRules()

    test_dir_1 = Path("test_dir_1")
    test_dir_2 = Path("test_dir_2")
    test_dir_3 = Path("test_dir_3")
    test_dir_4 = Path("test_dir_4")
    test_file_1 = Path("test_file_1.txt")
    test_file_2 = Path("test_file_2.txt")

    # Single directory
    source = test_dir_1
    destination_dir = test_dir_3
    _doMove(source, destination_dir)
    assert source.exists() is False
    assert destination_dir.exists() is True
    assert destination_dir.is_dir() is True

    # Single directory with renaming
    source = test_dir_2
    destination_dir = test_dir_3 / "moved_dir"
    _doMove(source, destination_dir)
    assert source.exists() is False
    assert destination_dir.exists() is True
    assert destination_dir.is_dir() is True

    # Multiple directories
    sources = [test_dir_3, test_file_1]
    destination_dir = test_dir_4
    # breakpoint()
    _doMove(sources, destination_dir)
    assert all([_.exists() is False for _ in sources])
    assert (destination_dir / sources[0]).exists() is True
    assert (destination_dir / sources[0]).is_dir() is True
    assert (destination_dir / sources[1]).exists() is True
    assert (destination_dir / sources[1]).is_file() is True

    # Non-existent source directory
    source = "nonexistent_dir"
    destination = test_dir_4
    with raises(FileNotFoundError):
        _doMove(source, destination)

    # Non-existent destination directory
    source = [test_file_2, test_dir_4]
    destination = "nonexistent_dir"
    with raises(FileNotFoundError):
        _doMove(source, destination)


@test("Basic remove operations.")
@xfail
def test_removeFileOperations():
    """Basic remove operations."""
    raise NotImplementedError
    # === Remove ===
    # Files (single, multiple, non-existant)
    # Directorie (single, multiple, non-existant, not empty)


@test("Basic tar operations - single file")
def test_10_tarSingleFile(_=setupTestCopyMove):
    """Creates a tar archive from a single file."""
    def _doTar(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_archive = Path("archive.tar")

    # Create the source file
    with open(test_file_1, "w") as f:
        f.write("This is a test file.")

    _doTar(test_file_1, test_archive)

    # Make sure file does not exists except in archive
    os.remove(test_file_1)

    # Verify the archive exists
    assert test_archive.exists() is True

    # Extract the archive and verify content
    with tarfile.open(test_archive) as tarball:
        tarball.extractall()
    with open(test_file_1, "r") as f:
        content = f.read()
    assert content == "This is a test file."

    # Clean up
    os.remove(test_file_1)
    os.remove(test_archive)


@test("Basic tar operations - single file with rename")
@xfail
def test_11_tarSingleFileRename(_=setupTestCopyMove):
    """Creates a tar archive from a single file with a custom name in the archive."""
    raise NotImplementedError
    # def _doTar(src, dst):
    #     getCurrentContext().clearRules()
    #     Rule(deps=src, targets=dst, builder=tar).apply()
    #     getCurrentContext().clearRules()

    # test_file_1 = Path("test_file_1.txt")
    # test_archive = Path("archive.tar")

    # # Create the source file
    # with open(test_file_1, "w") as f:
    #     f.write("This is a test file.")

    # # Will fail here, currently no way to pass no name inside rule structure.
    # _doTar((test_file_1, "custom_name_in_tar.txt"), test_archive)

    # # Verify the archive exists
    # assert test_archive.exists() is True

    # # Extract the archive and verify content
    # with tarfile.open(test_archive) as tarball:
    #     tarball.extractall()
    # with open("custom_name.txt", "r") as f:
    #     content = f.read()
    # assert content == "This is a test file."

    # # Clean up
    # os.remove("custom_name.txt")
    # os.remove(test_archive)


@test("Basic tar operations - multiple files")
def test_12_tarMultipleFiles(_=setupTestCopyMove):
    """Creates a tar archive from multiple files."""
    def _doTar(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_file_2 = Path("test_file_2.txt")
    test_archive = Path("archive.tar")

    # Create the source files
    with open(test_file_1, "w") as f:
        f.write("This is a test file 1.")
    with open(test_file_2, "w") as f:
        f.write("This is a test file 2.")

    _doTar([test_file_1, test_file_2], test_archive)

    # Make sure files does not exists except in archive
    os.remove(test_file_1)
    os.remove(test_file_2)

    # Verify the archive exists
    assert test_archive.exists() is True

    # Extract the archive and verify content
    with tarfile.open(test_archive) as tarball:
        tarball.extractall()
    with open(test_file_1, "r") as f:
        content = f.read()
    assert content == "This is a test file 1."
    with open(test_file_2, "r") as f:
        content = f.read()
    assert content == "This is a test file 2."

    # Clean up
    os.remove(test_file_1)
    os.remove(test_file_2)
    os.remove(test_archive)


@test("Basic tar operations - directory")
def test_13_tarDirectory(_=setupTestCopyMove):
    """Creates a tar archive from a directory."""
    def _doTar(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar).apply()
        getCurrentContext().clearRules()

    test_dir_1 = Path("test_dir_1")
    test_file_3 = test_dir_1 / "test_file_3.txt"
    test_archive = Path("archive.tar")

    _doTar(test_dir_1, test_archive)

    # Make sure files does not exists except in archive
    shutil.rmtree(test_dir_1)

    # Verify the archive exists
    assert test_archive.exists() is True

    # Extract the archive and verify content
    with tarfile.open(test_archive) as tarball:
        tarball.extractall()
    with open(test_file_3, "r") as f:
        content = f.read()
    assert content == "Another other test file."

    # Clean up
    shutil.rmtree(test_dir_1)
    os.remove(test_archive)


@test("Basic tar operations - link")
def test_14_tarLink(_=setupTestCopyMove):
    """Creates a tar archive from a symbolic link."""
    def _doTar(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar).apply()
        getCurrentContext().clearRules()

    test_file_1 = Path("test_file_1.txt")
    test_link = Path("link_to_file_1.lnk")
    test_archive = Path("archive.tar")

    _doTar(test_link, test_archive)

    # Make sure files does not exists except in archive
    os.remove(test_link)

    # Verify the archive exists
    assert test_archive.exists() is True

    # Extract the archive and verify content (link will be recreated as a file)
    with tarfile.open(test_archive) as tarball:
        tarball.extractall()
    with open(test_link.resolve(), "r") as f:
        contentLink = f.read()
    with open(test_file_1, "r") as f:
        contentFile = f.read()
    assert contentLink == contentFile

    # Clean up
    os.remove(test_file_1)
    os.remove(test_link)
    os.remove(test_archive)


@test("Tar errors - non-existent source")
def test_15_tarNonexistentSource(_=setupTestCopyMove):
    """Attempts to create a tar archive from a non-existent source and raises an error."""
    def _doTar(src, dst):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar).apply()
        getCurrentContext().clearRules()

    test_archive = Path("archive.tar.gz")
    source = Path("nonexistent_file.txt")

    with raises(FileNotFoundError):
        _doTar(source, test_archive)

    # Clean up (archive won't be created)
    assert not test_archive.exists()


@test("Tar with compression options")
def test_16_tarCompression(_=setupTestCopyMove):
    """Creates a tar archive with different compression options."""
    def _doTar(src, dst, compression):
        getCurrentContext().clearRules()
        Rule(deps=src, targets=dst, builder=tar, compression=compression).apply()
        getCurrentContext().clearRules()

    test_dir_1 = Path("test_dir_1")
    test_file_1 = test_dir_1 / "test_file_1.txt"
    test_archive_gz = Path("archive.tar.gz")
    test_archive_bz2 = Path("archive.tar.bz2")
    test_archive_xz = Path("archive.tar.xz")

    # Create the source directory and file
    os.makedirs(test_dir_1, exist_ok=True)
    with open(test_file_1, "w") as f:
        f.write("This is a test file.")

    # Create archives with different compression
    _doTar(test_dir_1, test_archive_gz, compression="gz")
    _doTar(test_dir_1, test_archive_bz2, compression="bz2")
    _doTar(test_dir_1, test_archive_xz, compression="xz")

    # Verify archives exist
    assert test_archive_gz.exists() is True
    assert test_archive_bz2.exists() is True
    assert test_archive_xz.exists() is True

    # Verify archive types
    tarfile.open(test_archive_gz, "r:gz").close()
    tarfile.open(test_archive_bz2, "r:bz2").close()
    tarfile.open(test_archive_xz, "r:xz").close()

    # Clean up
    shutil.rmtree(test_dir_1)
    os.remove(test_archive_gz)
    os.remove(test_archive_bz2)
    os.remove(test_archive_xz)
