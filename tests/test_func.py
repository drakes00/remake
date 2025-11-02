#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional test cases."""

import os
import glob
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
    os.makedirs("/tmp/remake", exist_ok=True)
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

    for f in glob.glob("/tmp/remake/*"):
        try:
            assert f.startswith("/tmp")
            os.remove(f)
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

    for f in glob.glob("/tmp/remake/*"):
        try:
            assert f.startswith("/tmp")
            os.remove(f)
        except FileNotFoundError:
            pass

    # Return where we were.
    os.chdir(prev_dir)


@test("Correctly computes virtual dependency trees")
def test_01_funDepsVirt(_=ensureCleanContext):
    """Correctly computes virtual dependency trees"""

    setDryRun()
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
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
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
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    assert findBuildPath(pathlib.Path("b")) != findBuildPath(VirtualTarget("b"))
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
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # One file two dependencies with two rules.
    # r_4_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    # r_4_2 = Rule(targets="a", deps="c", builder=fooBuilder)
    # FIXME: Should raise or r_4_2 should replace r_4_1
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
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
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
    assert findBuildPath(pathlib.Path("d")) != findBuildPath(VirtualTarget("d"))
    getCurrentContext().clearRules()

    # Simple rule with another rule with multiple targets
    r_7_1 = Rule(targets=[VirtualTarget("a"), VirtualTarget("b")], deps=VirtualDep("c"), builder=fooBuilder)
    r_7_2 = Rule(targets=VirtualTarget("d"), deps=[VirtualDep("e"), VirtualDep("f")], builder=fooBuilder)
    r_7_3 = Rule(
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
         r_7_1): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    assert findBuildPath(VirtualTarget("b")) == {
        (VirtualTarget("b"),
         r_7_1): [{
            (VirtualDep("c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("b")) != findBuildPath(VirtualTarget("b"))
    assert findBuildPath(VirtualTarget("d")) == {
        (VirtualTarget("d"),
         r_7_2): [
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
    assert findBuildPath(pathlib.Path("d")) != findBuildPath(VirtualTarget("d"))
    assert findBuildPath(VirtualTarget("g")) == {
        (VirtualTarget("g"),
         r_7_3): [
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
    assert findBuildPath(pathlib.Path("g")) != findBuildPath(VirtualTarget("g"))
    assert findBuildPath(VirtualTarget("h")) == {
        (VirtualTarget("h"),
         r_7_3): [
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
    assert findBuildPath(pathlib.Path("h")) != findBuildPath(VirtualTarget("h"))
    getCurrentContext().clearRules()


@test("Correctly computes virtual dependency trees")
def test_02_funDepsPath(_=ensureCleanContext):
    """Correctly computes virtual dependency trees"""

    setDryRun()
    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    os.chdir("/tmp")

    # One file one dependence.
    r_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_1): [{
            (pathlib.Path("/tmp/b"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("a")) == findBuildPath(pathlib.Path("/tmp/a"))
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # Two files one dependence.
    r_2_1 = Rule(targets=pathlib.Path("a"), deps=pathlib.Path("c"), builder=fooBuilder)
    r_2_2 = Rule(targets=pathlib.Path("b"), deps=pathlib.Path("c"), builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_2_1): [{
            (pathlib.Path("/tmp/c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("b")) == {
        (pathlib.Path("/tmp/b"),
         r_2_2): [{
            (pathlib.Path("/tmp/c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("a")) == findBuildPath(pathlib.Path("/tmp/a"))
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    assert findBuildPath(pathlib.Path("b")) == findBuildPath(pathlib.Path("/tmp/b"))
    assert findBuildPath(pathlib.Path("b")) != findBuildPath(VirtualTarget("b"))
    getCurrentContext().clearRules()

    # One file two dependencies
    r_3_1 = Rule(targets=pathlib.Path("a"), deps=[pathlib.Path("b"), pathlib.Path("c")], builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_3_1): [
            {
                (pathlib.Path("/tmp/b"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/c"),
                 None): []
            },
        ]
    }
    assert findBuildPath(pathlib.Path("a")) == findBuildPath(pathlib.Path("/tmp/a"))
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # One file two dependencies with two rules.
    # r_4_1 = Rule(targets="a", deps="b", builder=fooBuilder)
    # r_4_2 = Rule(targets="a", deps="c", builder=fooBuilder)
    # FIXME: Should raise or r_4_2 should replace r_4_1
    # assert findBuildPath(pathlib.Path("a")) == {("/tmp/a", r_4_1): ["/tmp/b", "/tmp/c"]}
    # getCurrentContext().clearRules()

    # Three levels
    r_5_1 = Rule(targets=pathlib.Path("a"), deps=pathlib.Path("b"), builder=fooBuilder)
    r_5_2 = Rule(targets=pathlib.Path("b"), deps=pathlib.Path("c"), builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_5_1): [{
            (pathlib.Path("/tmp/b"),
             r_5_2): [{
                (pathlib.Path("/tmp/c"),
                 None): []
            }]
        }]
    }
    assert findBuildPath(pathlib.Path("a")) == findBuildPath(pathlib.Path("/tmp/a"))
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))
    getCurrentContext().clearRules()

    # Complex
    r_6_1 = Rule(
        targets=pathlib.Path("d"),
        deps=[
            pathlib.Path("c"),
            pathlib.Path("a2"),
            pathlib.Path("b1"),
        ],
        builder=fooBuilder,
    )
    r_6_2 = Rule(
        targets=pathlib.Path("c"),
        deps=[
            pathlib.Path("b1"),
            pathlib.Path("b2"),
        ],
        builder=fooBuilder,
    )
    r_6_3 = Rule(
        targets=pathlib.Path("b1"),
        deps=[
            pathlib.Path("a1"),
        ],
        builder=fooBuilder,
    )
    r_6_4 = Rule(
        targets=pathlib.Path("b2"),
        deps=[
            pathlib.Path("a1"),
            pathlib.Path("a2"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath(pathlib.Path("d")) == {
        (pathlib.Path("/tmp/d"),
         r_6_1):
            [
                {
                    (pathlib.Path("/tmp/c"),
                     r_6_2):
                        [
                            {
                                (pathlib.Path("/tmp/b1"),
                                 r_6_3): [{
                                    (pathlib.Path("/tmp/a1"),
                                     None): []
                                },
                                         ]
                            },
                            {
                                (pathlib.Path("/tmp/b2"),
                                 r_6_4): [
                                    {
                                        (pathlib.Path("/tmp/a1"),
                                         None): []
                                    },
                                    {
                                        (pathlib.Path("/tmp/a2"),
                                         None): []
                                    },
                                ]
                            }
                        ]
                },
                {
                    (pathlib.Path("/tmp/a2"),
                     None): []
                },
                {
                    (pathlib.Path("/tmp/b1"),
                     r_6_3): [{
                        (pathlib.Path("/tmp/a1"),
                         None): []
                    }]
                }
            ]
    }
    assert findBuildPath(pathlib.Path("d")) == findBuildPath(pathlib.Path("/tmp/d"))
    assert findBuildPath(pathlib.Path("d")) != findBuildPath(VirtualTarget("d"))
    getCurrentContext().clearRules()

    # Simple rule with another rule with multiple targets
    r_7_1 = Rule(targets=[pathlib.Path("a"), pathlib.Path("b")], deps=pathlib.Path("c"), builder=fooBuilder)
    r_7_2 = Rule(targets=pathlib.Path("d"), deps=[pathlib.Path("e"), pathlib.Path("f")], builder=fooBuilder)
    r_7_3 = Rule(
        targets=[
            pathlib.Path("g"),
            pathlib.Path("h"),
        ],
        deps=[
            pathlib.Path("i"),
            pathlib.Path("j"),
        ],
        builder=fooBuilder,
    )
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_7_1): [{
            (pathlib.Path("/tmp/c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("a")) == findBuildPath(pathlib.Path("/tmp/a"))
    assert findBuildPath(pathlib.Path("a")) != findBuildPath(VirtualTarget("a"))

    assert findBuildPath(pathlib.Path("b")) == {
        (pathlib.Path("/tmp/b"),
         r_7_1): [{
            (pathlib.Path("/tmp/c"),
             None): []
        }]
    }
    assert findBuildPath(pathlib.Path("b")) == findBuildPath(pathlib.Path("/tmp/b"))
    assert findBuildPath(pathlib.Path("b")) != findBuildPath(VirtualTarget("b"))

    assert findBuildPath(pathlib.Path("d")) == {
        (pathlib.Path("/tmp/d"),
         r_7_2): [
            {
                (pathlib.Path("/tmp/e"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/f"),
                 None): []
            },
        ]
    }
    assert findBuildPath(pathlib.Path("d")) == findBuildPath(pathlib.Path("/tmp/d"))
    assert findBuildPath(pathlib.Path("d")) != findBuildPath(VirtualTarget("d"))

    assert findBuildPath(pathlib.Path("g")) == {
        (pathlib.Path("/tmp/g"),
         r_7_3): [
            {
                (pathlib.Path("/tmp/i"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/j"),
                 None): []
            },
        ]
    }
    assert findBuildPath(pathlib.Path("g")) == findBuildPath(pathlib.Path("/tmp/g"))
    assert findBuildPath(pathlib.Path("g")) != findBuildPath(VirtualTarget("g"))

    assert findBuildPath(pathlib.Path("h")) == {
        (pathlib.Path("/tmp/h"),
         r_7_3): [
            {
                (pathlib.Path("/tmp/i"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/j"),
                 None): []
            },
        ]
    }
    assert findBuildPath(pathlib.Path("h")) == findBuildPath(pathlib.Path("/tmp/h"))
    assert findBuildPath(pathlib.Path("h")) != findBuildPath(VirtualTarget("h"))
    getCurrentContext().clearRules()


@test("Correctly computes mixed path/virtual dependency trees")
def test_03_funDepsMixed(_=ensureCleanContext):
    """Correctly computes mixed path/virtual dependency trees"""

    setDryRun()
    setDevTest()
    fooBuilder = Builder(action="Magically creating $@ from $<")

    os.chdir("/tmp")

    # Case 1: File depending on a virtual dependency.
    r_1 = Rule(targets="a", deps=VirtualDep("b"), builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_1): [{
            (VirtualDep("b"),
             None): []
        }]
    }
    getCurrentContext().clearRules()

    # Case 2: Virtual target depending on a file.
    r_2 = Rule(targets=VirtualTarget("a"), deps="b", builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_2): [{
            (pathlib.Path("/tmp/b"),
             None): []
        }]
    }
    getCurrentContext().clearRules()

    # Case 3: File depending on a virtual dep and a file.
    r_3 = Rule(targets="a", deps=[VirtualDep("b"), "c"], builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_3): [
            {
                (VirtualDep("b"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/c"),
                 None): []
            },
        ]
    }
    getCurrentContext().clearRules()

    # Case 4: Virtual target depending on a virtual dep and a file.
    r_4 = Rule(targets=VirtualTarget("a"), deps=[VirtualDep("b"), "c"], builder=fooBuilder)
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_4): [
            {
                (VirtualDep("b"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/c"),
                 None): []
            },
        ]
    }
    getCurrentContext().clearRules()

    # Case 5: Multi-level dependencies with mixed types.
    r_5_1 = Rule(targets="a", deps=VirtualDep("b"), builder=fooBuilder)
    r_5_2 = Rule(targets=VirtualTarget("b"), deps="c", builder=fooBuilder)
    assert findBuildPath(pathlib.Path("a")) == {
        (pathlib.Path("/tmp/a"),
         r_5_1): [{
            (VirtualTarget("b"),
             r_5_2): [{
                (pathlib.Path("/tmp/c"),
                 None): []
            }]
        }]
    }
    getCurrentContext().clearRules()

    # Case 6: Complex mixed dependency tree.
    r_6_1 = Rule(targets="d", deps=[VirtualDep("c"), "b1"], builder=fooBuilder)
    r_6_2 = Rule(targets=VirtualTarget("c"), deps=["b1", VirtualDep("b2")], builder=fooBuilder)
    r_6_3 = Rule(targets="b1", deps=["a1"], builder=fooBuilder)
    r_6_4 = Rule(targets=VirtualTarget("b2"), deps=["a1", VirtualDep("a2")], builder=fooBuilder)
    assert findBuildPath(pathlib.Path("d")) == {
        (pathlib.Path("/tmp/d"),
         r_6_1):
            [
                {
                    (VirtualTarget("c"),
                     r_6_2):
                        [
                            {
                                (pathlib.Path("/tmp/b1"),
                                 r_6_3): [{
                                    (pathlib.Path("/tmp/a1"),
                                     None): []
                                }]
                            },
                            {
                                (VirtualTarget("b2"),
                                 r_6_4): [
                                    {
                                        (pathlib.Path("/tmp/a1"),
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
                    (pathlib.Path("/tmp/b1"),
                     r_6_3): [{
                        (pathlib.Path("/tmp/a1"),
                         None): []
                    }]
                }
            ]
    }
    getCurrentContext().clearRules()

    # Case 7: Rule with multiple mixed targets and deps.
    r_7 = Rule(targets=[VirtualTarget("a"), "b"], deps=[VirtualDep("c"), "d"], builder=fooBuilder)
    # Test for virtual target 'a'
    assert findBuildPath(VirtualTarget("a")) == {
        (VirtualTarget("a"),
         r_7): [
            {
                (VirtualDep("c"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/d"),
                 None): []
            },
        ]
    }
    # Test for path target 'b'
    assert findBuildPath(pathlib.Path("b")) == {
        (pathlib.Path("/tmp/b"),
         r_7): [
            {
                (VirtualDep("c"),
                 None): []
            },
            {
                (pathlib.Path("/tmp/d"),
                 None): []
            },
        ]
    }
    depA = findBuildPath(VirtualTarget("a"))[(VirtualTarget("a"), r_7)]
    depB = findBuildPath(pathlib.Path("b"))[(pathlib.Path("/tmp/b"), r_7)]
    assert depA == depB
    getCurrentContext().clearRules()


@test("Dependency can appear multiple times in the tree")
def test_04_funDepsMultipleTimes(_=ensureCleanContext):
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
def test_05_funSameRuleTwice(_=ensureCleanContext):
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
def test_06_funMakeTarget(_=ensureCleanContext):
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
def test_07_generateAllTargetsOfPatternRules(_=ensureCleanContext, _2=ensureEmptyTmp):
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
def test_08_funDepsMultipleTargets(_=ensureCleanContext):
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
def test_09_ruleMultipleTargetsExecutedOnce(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Rule with multiple targets is executed only once to make all targets"""

    setDevTest()
    setDryRun()
    os.chdir("/tmp/remake")
    fooBuilder = Builder(action="Magically creating $@ from $<")
    r_1 = Rule(targets=["a", "b"], deps="c", builder=fooBuilder)
    r_2 = Rule(targets=["d", "e"], deps="a", builder=fooBuilder)
    AddTarget("a")
    AddTarget("b")
    AddTarget("d")
    AddTarget("e")
    os.chdir("/tmp/remake")
    assert buildDeps(generateDependencyList()) == [
        ([pathlib.Path("/tmp/remake/a"),
          pathlib.Path("/tmp/remake/b")],
         r_1),
        ([pathlib.Path("/tmp/remake/d"),
          pathlib.Path("/tmp/remake/e")],
         r_2)
    ]


@test("Dependencies can be cleaned")
def test_10_cleanDependencies(_=ensureCleanContext, _2=ensureEmptyTmp):
    """Dependencies can be cleaned"""

    touchBuilder = Builder(action="touch $@")

    # Ensure file does not already exist.
    os.chdir("/tmp/remake")
    try:
        os.remove(f"{TMP_FILE}")
    except FileNotFoundError:
        pass

    # With a real dependency.
    r_1 = Rule(targets=f"{TMP_FILE}", deps=[], builder=touchBuilder)
    AddTarget(TMP_FILE)
    assert buildDeps(generateDependencyList()) == [([pathlib.Path(TMP_FILE)], r_1)]
    assert os.path.isfile(TMP_FILE)
    assert cleanDeps(generateDependencyList()) == [pathlib.Path(TMP_FILE)]
    assert not os.path.isfile(TMP_FILE)
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Try with a virtual dependency.
    r_2 = Rule(targets=VirtualTarget("virtualdeptoclean"), deps=[], builder=touchBuilder)
    AddVirtualTarget("virtualdeptoclean")
    assert buildDeps(generateDependencyList()) == [([VirtualTarget("virtualdeptoclean")], r_2)]
    assert os.path.isfile("virtualdeptoclean")
    assert cleanDeps(generateDependencyList()) == []

    # File is not removed since virtual target are ignored on clean.
    assert os.path.isfile("virtualdeptoclean")
    os.remove("virtualdeptoclean")
    getCurrentContext().clearRules()
    getCurrentContext().clearTargets()

    # Try with a pattern rule.
    r_3 = PatternRule(target="*.tmp", deps=[], builder=touchBuilder)
    AddTarget("a.tmp")
    AddTarget("b.tmp")
    print()
    assert buildDeps(generateDependencyList()) == [
        ([pathlib.Path("/tmp/remake/a.tmp")],
         r_3.expand(pathlib.Path("a.tmp"))),
        ([pathlib.Path("/tmp/remake/b.tmp")],
         r_3.expand(pathlib.Path("b.tmp")))
    ]
    assert os.path.isfile("/tmp/remake/a.tmp")
    assert os.path.isfile("/tmp/remake/b.tmp")
    assert cleanDeps(generateDependencyList()) == [pathlib.Path("/tmp/remake/a.tmp"), pathlib.Path("/tmp/remake/b.tmp")]
    assert not os.path.isfile("/tmp/remake/a.tmp")
    assert not os.path.isfile("/tmp/remake/b.tmp")
