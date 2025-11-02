#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional test cases."""

import os
import pathlib
import shutil

from ward import test, raises, fixture

from remake import Builder, Rule, PatternRule, AddTarget, AddVirtualTarget, VirtualTarget, VirtualDep
from remake import findBuildPath, buildDeps, cleanDeps, generateDependencyList, getCurrentContext
from remake import setDryRun, setDevTest, unsetDryRun, unsetDevTest

TMP_FILE = "/tmp/remake.tmp"


@fixture
def ensureCleanContext():
    """Cleans rules and targets and unsets dev mode and dry mode between tests."""

    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    yield
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()
    unsetDryRun()
    unsetDevTest()


@fixture
def ensureEmptyTmp():
    """Ensures that all ReMake related files created in /tmp are emptied between tests."""

    # Save current directory.
    prev_dir = os.getcwd()

    os.chdir("/tmp")
    try:
        os.remove("/tmp/ReMakeFile")
    except FileNotFoundError:
        pass

    for f in ("/tmp/remake_subdir", "/tmp/remake_subdir2"):
        try:
            assert f.startswith("/tmp")
            shutil.rmtree(f)
        except FileNotFoundError:
            pass

    yield
    os.chdir("/tmp")

    try:
        os.remove("/tmp/ReMakeFile")
    except FileNotFoundError:
        pass

    for f in ("/tmp/remake_subdir", "/tmp/remake_subdir2"):
        try:
            assert f.startswith("/tmp")
            shutil.rmtree(f)
        except FileNotFoundError:
            pass

    # Return where we were.
    os.chdir(prev_dir)

@test("Automatically detect dependencies")
def test_01_funDeps(_=ensureCleanContext):
    """Automatically detect dependencies"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    r_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_1): [{
            (VirtualDep("b"),
             None): []
        }]
    }
    assert findBuildPath("a") == findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # Two files one dependence.
    r_2_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("c"), builder=fooBuilder)
    r_2_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_2_1): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath(VirtualTarget("b")) == {
        (VirtualTarget("b"),
         r_2_2): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath("a") == findBuildPath(VirtualTarget("a"))
    assert findBuildPath("b") == findBuildPath(VirtualTarget("b"))
    getCurrentContext().clearRules()

    # One file two dependencies
    r_3_1 = Rule(targets=VirtualTarget("a"), deps=[VirtualDep("b"), VirtualDep("c")], builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_3_1): [
            {
                (VirtualDep("b"),
                 None): []
            },
            {
                (VirtualDep("c"),
                 None): []
            },
        ]
    }
    assert findBuildPath("a") == findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # One file two dependencies with two rules.
    # r_4_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    # r_4_2 = Rule(targets="a", deps="c", builder=fooBuilder)
    # FIXME Should raise or r_4_2 should replace r_4_1
    # assert findBuildPath(VirtualTarget("a")) == {("/tmp/a", r_4_1): ["/tmp/b", "/tmp/c"]}
    # getCurrentContext().clearRules()

    # Three levels
    r_5_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    r_5_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_5_1): [{
            (VirtualTarget("b"),
             r_5_2): [{
                (VirtualDep("c"),
                 None): []
            }]
        }]
    }
    assert findBuildPath("a") == findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # Complex
    r_6_1 = Rule(
        targets=VirtualTarget("d"),
        deps=[
            VirtualDep("c"),
            VirtualDep("a2"),
            VirtualDep("b1"),
        ],
        builder=fooBuilder,
    )
    r_6_2 = Rule(
        targets=VirtualTarget("c"),
        deps=[
            VirtualDep("b1"),
            VirtualDep("b2"),
        ],
        builder=fooBuilder,
    )
    r_6_3 = Rule(
        targets=VirtualTarget("b1"),
        deps=[
            VirtualDep("a1"),
        ],
        builder=fooBuilder,
    )
    r_6_4 = Rule(
        targets=VirtualTarget("b2"),
        deps=[
            VirtualDep("a1"),
            VirtualDep("a2"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath(VirtualTarget("d")) == {
        (VirtualTarget("d"),
         r_6_1):
            [
                {
                    (VirtualTarget("c"),
                     r_6_2):
                        [
                            {
                                (VirtualTarget("b1"),
                                 r_6_3): [{
                                    (VirtualDep("a1"),
                                     None): []
                                },
                                         ]
                            },
                            {
                                (VirtualTarget("b2"),
                                 r_6_4): [
                                    {
                                        (VirtualDep("a1"),
                                         None): []
                                    },
                                    {
                                        (VirtualDep("a2"),
                                         None): []
                                    },
                                ]
                            }
                        ]
                },
                {
                    (VirtualDep("a2"),
                     None): []
                },
                {
                    (VirtualTarget("b1"),
                     r_6_3): [{
                        (VirtualDep("a1"),
                         None): []
                    }]
                }
            ]
    }
    assert findBuildPath("d") == findBuildPath(VirtualTarget("d"))
    getCurrentContext().clearRules()

    # Simple rule with another rule with multiple targets
    r_8_1 = Rule(targets=[VirtualTarget("a"), VirtualTarget("b")], deps=VirtualDep("c"), builder=fooBuilder)
    r_8_2 = Rule(targets=VirtualTarget("d"), deps=[VirtualDep("e"), VirtualDep("f")], builder=fooBuilder)
    r_8_3 = Rule(
        targets=[
            VirtualTarget("g"),
            VirtualTarget("h"),
        ],
        deps=[
            VirtualDep("i"),
            VirtualDep("j"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_8_1): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath("a") == findBuildPath(VirtualTarget("a"))
    assert findBuildPath(VirtualTarget("b")) == {
        (VirtualTarget("b"),
         r_8_1): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath("b") == findBuildPath(VirtualTarget("b"))
    assert findBuildPath(VirtualTarget("d")) == {
        (VirtualTarget("d"),
         r_8_2): [
            {
                (VirtualDep("e"),
                 None): []
            },
            {
                (VirtualDep("f"),
                 None): []
            },
        ]
    }
    assert findBuildPath("d") == findBuildPath(VirtualTarget("d"))
    assert findBuildPath(VirtualTarget("g")) == {
        (VirtualTarget("g"),
         r_8_3): [
            {
                (VirtualDep("i"),
                 None): []
            },
            {
                (VirtualDep("j"),
                 None): []
            },
        ]
    }
    assert findBuildPath("g") == findBuildPath(VirtualTarget("g"))
    assert findBuildPath(VirtualTarget("h")) == {
        (VirtualTarget("h"),
         r_8_3): [
            {
                (VirtualDep("i"),
                 None): []
            },
            {
                (VirtualDep("j"),
                 None): []
            },
        ]
    }
    assert findBuildPath("h") == findBuildPath(VirtualTarget("h"))
    getCurrentContext().clearRules()


@test("Dependency can appear multiple times in the tree")
def test_02_funDepsMultipleTimes(_=ensureCleanContext):
    """Dependency can appear multiple times in the tree"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    r_1 = Rule(targets=VirtualTarget("a"), deps=[VirtualDep("b"), VirtualDep("c")], builder=fooBuilder)
    r_2 = Rule(targets=VirtualTarget("b"), deps=VirtualDep("c"), builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_1): [
            {
                (VirtualTarget("b"),
                 r_2): [{
                    (VirtualDep("c"),
                     None): []
                }]
            },
            {
                (VirtualDep("c"),
                 None): []
            },
        ]
    }


@test("Same rule applied twice should be ignored")
def test_03_funSameRuleTwice(_=ensureCleanContext):
    """Same rule applied twice should be ignored"""

    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # One file one dependence.
    r_1 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    r_2 = Rule(targets=VirtualTarget("a"), deps=VirtualDep("b"), builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_1): [{
            (VirtualDep("b"),
             None): []
        }]
    }
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_2): [{
            (VirtualDep("b"),
             None): []
        }]
    }


@test("Rules must make targets")
def test_04_funMakeTarget(_=ensureCleanContext):
    """Rules must make targets"""

    fooBuilder = Builder(action="ls > /dev/null")
    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # Ensure rule not making the target file will throw.
    rule = Rule(targets=f"{TMP_FILE}", deps=[], builder=fooBuilder)
    with raises(FileNotFoundError):
        rule.apply()
    getCurrentContext().clearRules()

    rule = Rule(targets=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    rule.apply()
    assert os.path.isfile(TMP_FILE)
    os.remove(TMP_FILE)


@test("Can generate all targets from a pattern rule (with a glob call)")
def test_05_generateAllTargetsOfPatternRules(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Can generate all targets from a pattern rule (with a glob call)"""

    os.mkdir("/tmp/remake_subdir")
    os.mkdir("/tmp/remake_subdir/foo")
    os.mkdir("/tmp/remake_subdir/foo/bar")
    pathlib.Path("/tmp/remake_subdir/non.x").touch()
    pathlib.Path("/tmp/remake_subdir/foo/a.x").touch()
    pathlib.Path("/tmp/remake_subdir/foo/b.x").touch()
    pathlib.Path("/tmp/remake_subdir/foo/bar/c.x").touch()
    pathlib.Path("/tmp/remake_subdir/foo/bar/d.x").touch()

    os.chdir("/tmp/remake_subdir/foo")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    rule = PatternRule(target="*.y", deps="*.x", builder=fooBuilder)
    assert sorted(rule.allTargets) == sorted(
        [pathlib.Path("a.y"),
         pathlib.Path("b.y"),
         pathlib.Path("bar/c.y"),
         pathlib.Path("bar/d.y")]
    )


@test("Automatically detect dependencies with multiple targets")
def test_06_funDepsMultipleTargets(_=ensureCleanContext):
    """Automatically detect dependencies with multiple targets"""

    setDryRun()
    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")

    # Two deps same rule.
    r_1 = Rule(targets="a", deps=["b", "c"], builder=fooBuilder)
    AddTarget("a")
    assert generateDependencyList() == [
        ([pathlib.Path("/tmp/c")],
         None),
        ([pathlib.Path("/tmp/b")],
         None),
        ([pathlib.Path("/tmp/a")],
         r_1),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two targets same rule.
    r_2 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    assert generateDependencyList() == [
        ([pathlib.Path("/tmp/c")],
         None),
        ([pathlib.Path("/tmp/a"),
          pathlib.Path("/tmp/b")],
         r_2),
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two targets same rule (no deps).
    r_3 = Rule(targets=["a", "b"], builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    assert generateDependencyList() == [([pathlib.Path("/tmp/a"), pathlib.Path("/tmp/b")], r_3)]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Three targets same rule.
    r_4 = Rule(targets=["a", "b", "c"], deps="d", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    AddTarget("c")
    assert generateDependencyList() == [
        ([pathlib.Path("/tmp/d")],
         None),
        ([pathlib.Path("/tmp/a"),
          pathlib.Path("/tmp/b"),
          pathlib.Path("/tmp/c")],
         r_4)
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two targets two same rules.
    r_5_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_5_2 = Rule(targets=["d", "e"], deps="f", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    AddTarget("d")
    AddTarget("e")
    assert generateDependencyList() == [
        ([pathlib.Path("/tmp/c")],
         None),
        ([pathlib.Path("/tmp/a"),
          pathlib.Path("/tmp/b")],
         r_5_1),
        ([pathlib.Path("/tmp/f")],
         None),
        ([pathlib.Path("/tmp/d"),
          pathlib.Path("/tmp/e")],
         r_5_2)
    ]
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Two levels.
    r_6_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_6_2 = Rule(targets=["d", "e"], deps="a", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    AddTarget("d")
    AddTarget("e")
    assert generateDependencyList() == [
        ([pathlib.Path("/tmp/c")],
         None),
        ([pathlib.Path("/tmp/a"),
          pathlib.Path("/tmp/b")],
         r_6_1),
        ([pathlib.Path("/tmp/d"),
          pathlib.Path("/tmp/e")],
         r_6_2)
    ]


@test("Rule with multiple targets is executed only once to make all targets")
def test_07_ruleMultipleTargetsExecutedOnce(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Rule with multiple targets is executed only once to make all targets"""

    setDevTest()
    setDryRun()
    os.chdir("/tmp")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_2 = Rule(targets=["d", "e"], deps="a", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    AddTarget("d")
    AddTarget("e")
    os.chdir("/tmp")
    assert buildDeps(generateDependencyList()) == [
        ([pathlib.Path("/tmp/a"),
          pathlib.Path("/tmp/b")],
         r_1),
        ([pathlib.Path("/tmp/d"),
          pathlib.Path("/tmp/e")],
         r_2)
    ]


@test("Dependencies can be cleaned")
def test_08_cleanDependencies(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Dependencies can be cleaned"""

    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    os.chdir("/tmp")
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # With a real dependency.
    r_1 = Rule(targets=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    AddTarget(TMP_FILE)
    assert buildDeps(generateDependencyList()) == [([pathlib.Path(TMP_FILE)], r_1)]
    assert os.path.isfile(TMP_FILE)
    assert cleanDeps(generateDependencyList()) == [([pathlib.Path(TMP_FILE)], r_1)]
    assert not os.path.isfile(TMP_FILE)
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Try with a virtual dependency.
    r_2 = Rule(targets=VirtualTarget("virtualdeptoclean"), deps=[], builder=touchBuilder)
    AddVirtualTarget("virtualdeptoclean")
    assert buildDeps(generateDependencyList()) == [([VirtualTarget("virtualdeptoclean")], r_2)]
    assert os.path.isfile("virtualdeptoclean")
    assert cleanDeps(generateDependencyList()) == [([VirtualTarget("virtualdeptoclean")], r_2)]

    # File is not removed since virtual target are ignored on clean.
    assert os.path.isfile("virtualdeptoclean")
    os.remove("virtualdeptoclean")
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Try with a pattern rule.
    # FIXME: Pattern rules currently do not support empty dependencies.
    # https://github.com/drakes00/remake/issues/13
    # r_3 = PatternRule(target="*.tmp", deps=[], builder=touchBuilder)
    # AddTarget("/tmp/a.tmp")
    # AddTarget("/tmp/b.tmp")
    # assert buildDeps(generateDependencyList()) == [([pathlib.Path("/tmp/a.tmp"), pathlib.Path("/tmp/b.tmp")], r_3)]
    # assert os.path.isfile("/tmp/a.tmp")
    # assert os.path.isfile("/tmp/b.tmp")
    # assert cleanDeps(generateDependencyList()) == [([pathlib.Path("/tmp/a.tmp"), pathlib.Path("/tmp/b.tmp")], r_3)]
    # assert not os.path.isfile("/tmp/a.tmp")
    # assert not os.path.isfile("/tmp/b.tmp")
