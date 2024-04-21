#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default builders for ReMake."""

import pathlib
import os
import shutil
import subprocess
import tarfile
import zipfile

from collections.abc import Callable
from rich.console import Console
from typeguard import typechecked

from remake.context import getCurrentContext
from remake.paths import VirtualTarget, VirtualDep, GlobPattern, shouldRebuild


@typechecked()
class Builder():
    """Generic builder class."""
    _action = None
    _shouldRebuild = None

    def __init__(
        self,
        action: list[str] | str | Callable[[list[str],
                                            list[str],
                                            Console],
                                           None],
        ephemeral: bool = False,
        shouldRebuildFun: Callable[[VirtualTarget | pathlib.Path,
                                    list[VirtualDep | pathlib.Path]],
                                   bool] | None = None,
    ):
        if isinstance(action, str):
            self._action = action.split(" ")
        else:
            self._action = action
        self._shouldRebuild = shouldRebuildFun
        if not ephemeral:
            self._register()

    def __eq__(self, other):
        return self._action == other._action

    def __hash__(self):
        if isinstance(self._action, list):
            return hash(tuple(self._action))  # Hash based on list action

        return hash(id(self._action))  # Hash based on function

    def _register(self) -> None:
        getCurrentContext().addBuilder(self)

    def parseAction(
        self,
        deps: list[VirtualDep | pathlib.Path | GlobPattern],
        targets: list[VirtualTarget | pathlib.Path | GlobPattern]
    ) -> list[str] | Callable[[list[str],
                               list[str],
                               Console],
                              None]:
        """Parses builder action for automatic variables ($@, etc)."""
        def _replace_in_action(llist, pattern, repl):
            try:
                i = llist.index(pattern)
            except ValueError:
                return llist
            return llist[:i] + repl + llist[i + 1:]

        if isinstance(self._action, list):
            ret = self._action
            ret = _replace_in_action(ret, "$@", targets)
            if deps:
                ret = _replace_in_action(ret, "$^", [deps[0]])
                ret = _replace_in_action(ret, "$<", deps)
            return ret

        return self._action

    @property
    def action(self) -> Callable[[list[str], list[str], Console], None]:
        """Returns builder's action."""
        return self._action

    @property
    def type(self):
        """Returns builder's action's type (list vs. callable)."""
        return type(self._action)

    @property
    def shouldRebuild(self):
        """Returns buider's custom shouldRebuild function."""
        return self._shouldRebuild


# ==================================================
# =              File Operations                   =
# ==================================================


def _FILE_OPS_shouldRebuild(target, deps):
    if len(deps) > 1:
        ret = False
        for dep in deps:
            ret = ret or shouldRebuild(target / dep.name, [dep])

        return ret

    dep = deps[0]
    if target.is_dir():
        target = target / dep.name

    return shouldRebuild(target, [dep])


# Expects either :
#   - 2 arguments (source, destination):
#       - If source is a file and dest does not exists -> Ok, rename as dest
#       - If source is a file and dest exists and is a file -> Ok, override
#       - If source is a file and dest exists and is a dir -> Ok, copy source into dest
#       - If source is a dir and dest does not exists, Ok, copy in dest's parent and rename as dest
#       - If source is a dir and dest exists and is a file, KO
#       - If source is a dir and dest exists and is a dir, Ok, copy source into dest
#   - Multiple arguments where all but last are source:
#       - last is the destination directory, must exists and everything is copied inside
#   - In all cases, intermediate folders must exist.
def _cp(deps, targets, _):
    assert len(targets) == 1
    target = targets[0]

    if len(deps) == 1 and deps[0].is_dir() and target.exists() and not target.is_dir():
        raise ValueError
    if len(deps) > 1 and not target.is_dir():
        raise FileNotFoundError

    if len(deps) > 1:
        for dep in deps:
            if dep.is_file():
                shutil.copy(dep, target)
            elif dep.is_dir():
                shutil.copytree(dep, target / dep.name)
    else:
        dep = deps[0]
        if dep.is_file():
            shutil.copy(dep, target)
        elif dep.is_dir() and target.is_dir():
            shutil.copytree(dep, target / dep.name)
        elif dep.is_dir() and not target.exists():
            shutil.copytree(dep, target)


cp = Builder(action=_cp, shouldRebuildFun=_FILE_OPS_shouldRebuild)


# Expects either :
#   - 2 arguments (source, destination):
#       - If source is a file and dest does not exists -> Ok, rename as dest
#       - If source is a file and dest exists and is a file -> Ok, override
#       - If source is a file and dest exists and is a dir -> Ok, move source into dest
#       - If source is a dir and dest does not exists, Ok, move in dest's parent and rename as dest
#       - If source is a dir and dest exists and is a file, KO
#       - If source is a dir and dest exists and is a dir, Ok, move source into dest
#   - Multiple arguments where all but last are source:
#       - last is the destination directory, must exists and everything is moved inside
#   - In all cases, intermediate folders must exist.
def _mv(deps, targets, _):
    # TODO Replace by copy then remove ?
    assert len(targets) == 1
    if len(deps) > 1 and not targets[0].is_dir():
        raise FileNotFoundError

    for dep in deps:
        shutil.move(dep, targets[0])


mv = Builder(action=_mv, shouldRebuildFun=_FILE_OPS_shouldRebuild)


def _rm(deps, targets, _):
    raise NotImplementedError


rm = Builder(action=_rm)

# ==================================================
# =                 Archives                       =
# ==================================================


def _tar(deps, targets, _, compression=""):
    cwd = os.getcwd()
    mode = f"w:{compression}" if compression in ("gz", "bz2", "xz") else "w"
    with tarfile.open(targets[0], mode, encoding="utf-8") as tar:
        for dep in deps:
            tar.add(dep.relative_to(cwd))


tar = Builder(action=_tar)


def _zip(deps, targets, _):
    cwd = os.getcwd()
    with zipfile.ZipFile(targets[0], "w") as zip:
        for dep in deps:
            if dep.is_dir():
                files = list(dep.rglob("*"))
                for file in files:
                    zip.write(file.relative_to(cwd))
            else:
                zip.write(dep.relative_to(cwd))


zip = Builder(action=_zip)

# ==================================================
# =              LaTeX Builders                    =
# ==================================================


def _tex2pdf(deps, _, _2, cmd="pdflatex"):
    latexFile = deps[0].replace(".tex", "")
    subprocess.run([cmd, latexFile], check=True)
    subprocess.run(["bibtex", latexFile], check=True)
    subprocess.run([cmd, latexFile], check=True)
    subprocess.run([cmd, latexFile], check=True)


tex2pdf = Builder(action=_tex2pdf)

# ==================================================
# =                C Builders                      =
# ==================================================


def _gcc(_, targets, _2, cflags=""):
    subprocess.run(["gcc", cflags, "-o", targets[0]], check=True)


gcc = Builder(action=_gcc)


def _clang(_, targets, _2, cflags=""):
    subprocess.run(["clang", cflags, "-o", targets[0]], check=True)


clang = Builder(action=_clang)

# ==================================================
# =              Other Builders                    =
# ==================================================

html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
md2html = Builder(action="pandoc $^ -o $@")
jinja2 = Builder(action="jinja2 $^ -o $@")
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")
