#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Default builders for ReMake.

This module defines the `Builder` class, which is the base for all builders in ReMake,
and a collection of default builders for common tasks. These builders can be used
directly in `remakefile.py` to define rules for building targets from dependencies.

The provided builders include:
- File operations: `cp` (copy), `mv` (move), `rm` (remove).
- Archive creation: `tar`, `zip`.
- Document compilation: `tex2pdf` (LaTeX to PDF).
- C/C++ compilation: `gcc`, `clang`.
- Other conversions: `html2pdf_chrome`, `md2html`, `jinja2`, `pdfcrop`.
"""

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
    """
    Represents a builder that can execute an action to create targets from dependencies.

    A builder can be configured with a command-line action (as a string or list of strings)
    or a Python callable. It can also have a custom function to determine if a target
    should be rebuilt.

    Attributes:
        _action (list[str] | str | Callable): The action to be executed by the builder.
        _shouldRebuild (Callable | None): A function to check if a target needs rebuilding.
        _destructive (bool): Whether the builder's action removes the target.
    """
    _action = None
    _shouldRebuild = None
    _destructive = None

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
        destructive: bool = False,
    ):
        """
        Initializes a Builder instance.

        Args:
            action: The action to perform. Can be a string (split into a command),
                    a list of strings (a command), or a callable.
            ephemeral: If True, the builder is not registered in the current context.
                       Defaults to False.
            shouldRebuildFun: A callable that determines if the target should be rebuilt.
                              It takes the target and dependencies as arguments and returns a boolean.
                              If None, the default logic is used.
            destructive: If True, the builder is considered destructive (e.g., `rm`).
                         Defaults to False.
        """
        if isinstance(action, str):
            self._action = action.split(" ")
        else:
            self._action = action
        self._shouldRebuild = shouldRebuildFun
        self._destructive = destructive
        if not ephemeral:
            self._register()

    def __eq__(self, other):
        """Checks if two Builder instances are equal based on their action."""
        return self._action == other._action

    def __hash__(self):
        """Computes the hash of a Builder instance based on its action."""
        if isinstance(self._action, list):
            return hash(tuple(self._action))  # Hash based on a list of actions

        return hash(id(self._action))  # Hash based on function

    def _register(self) -> None:
        """Registers the builder with the current ReMake context."""
        getCurrentContext().addBuilder(self)

    def parseAction(
        self,
        deps: list[VirtualDep | pathlib.Path | GlobPattern],
        targets: list[VirtualTarget | pathlib.Path | GlobPattern]
    ) -> list[str] | Callable[[list[str],
                               list[str],
                               Console],
                              None]:
        """
        Parses the builder's action, substituting automatic variables like $@, $^, and $<.

        - `$@`: Replaced by the list of targets.
        - `$^`: Replaced by the first dependency.
        - `$<`: Replaced by the list of all dependencies.

        Args:
            deps: The list of dependencies for the rule.
            targets: The list of targets for the rule.

        Returns:
            The parsed action, which is either a list of strings (for a command) or the original callable.
        """
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
    def action(self) -> list[str] | Callable[[list[str], list[str], Console], None]:
        """Returns the builder's action."""
        return self._action

    @property
    def type(self):
        """Returns the builder's action's type (list vs. callable)."""
        return type(self._action)

    @property
    def shouldRebuild(self):
        """Returns buider's custom shouldRebuild function."""
        return self._shouldRebuild

    @property
    def isDestructive(self):
        """Returns True if the builder is destructive (will remove target instead of creating it)."""
        return self._destructive


# ==================================================
# =              File Operations                   =
# ==================================================


def _FILE_OPS_shouldRebuild(target, deps):
    """
    Custom shouldRebuild function for file operations like copy and move.

    Determines if a target needs to be rebuilt based on the modification times
    of its dependencies. Handles cases where the target is a directory.

    Args:
        target: The target file or directory.
        deps: The list of dependency files or directories.

    Returns:
        True if the target should be rebuilt, False otherwise.
    """
    if len(deps) > 1:
        ret = False
        for dep in deps:
            ret = ret or shouldRebuild(target / dep.name, [dep])

        return ret

    dep = deps[0]
    if (dep.is_file() and target.is_dir()) or (dep.is_dir() and target.is_file()):
        return True

    if target.is_dir():
        target = target / dep.name

    return shouldRebuild(target, [dep])


def _cp(deps, targets, _):
    """
    Action for the 'cp' builder. Copies files and directories.

    This function mimics the behavior of the `cp` command-line utility.

    It expects either:
      - 2 arguments (source, destination):
          - If source is a file and dest does not exists -> Ok, rename as dest
          - If source is a file and dest exists and is a file -> Ok, override
          - If source is a file and dest exists and is a dir -> Ok, copy source into dest
          - If source is a dir and dest does not exists, Ok, copy in dest's parent and rename as dest
          - If source is a dir and dest exists and is a file, KO
          - If source is a dir and dest exists and is a dir, Ok, copy source into dest
      - Multiple arguments where all but last are source:
          - last is the destination directory, must exists and everything is copied inside
      - In all cases, intermediate folders must exist.

    Args:
        deps: List of source files/directories (dependencies).
        targets: List containing the destination file/directory (target).
        _: Unused console object.

    Raises:
        ValueError: If trying to copy a directory into a file.
        FileNotFoundError: If the target directory for multiple dependencies does not exist.
    """
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


# Builder for copying files and directories. See `_cp` for details.
cp = Builder(action=_cp, shouldRebuildFun=_FILE_OPS_shouldRebuild)


def _mv(deps, targets, _):
    """
    Action for the 'mv' builder. Moves files and directories.

    This function mimics the behavior of the `mv` command-line utility. It moves
    all dependency files/directories into the target directory.

    It expects either:
      - 2 arguments (source, destination):
          - If source is a file and dest does not exists -> Ok, rename as dest
          - If source is a file and dest exists and is a file -> Ok, override
          - If source is a file and dest exists and is a dir -> Ok, move source into dest
          - If source is a dir and dest does not exists, Ok, move in dest's parent and rename as dest
          - If source is a dir and dest exists and is a file, KO
          - If source is a dir and dest exists and is a dir, Ok, move source into dest
      - Multiple arguments where all but last are source:
          - last is the destination directory, must exists and everything is moved inside
      - In all cases, intermediate folders must exist.

    Args:
        deps: List of source files/directories (dependencies).
        targets: List containing the destination directory (target).
        _: Unused console object.

    Raises:
        FileNotFoundError: If the target directory for multiple dependencies does not exist.
    """
    # TODO Replace by copy then remove ?
    assert len(targets) == 1
    if len(deps) > 1 and not targets[0].is_dir():
        raise FileNotFoundError

    for dep in deps:
        shutil.move(dep, targets[0])


# Builder for moving files and directories. See `_mv` for details.
mv = Builder(action=_mv, shouldRebuildFun=_FILE_OPS_shouldRebuild)


def _FILE_OPS_rmShouldRebuild(target, _):
    """
    Custom shouldRebuild function for the 'rm' builder.

    The 'rm' action should only run if the target actually exists.

    Args:
        target: The target file or directory to be removed.
        _: Unused dependencies argument.

    Returns:
        True if the target exists, False otherwise.
    """
    if isinstance(target, VirtualTarget):
        return False
    else:
        return target.exists()


def _rm(deps, targets, _, recursive=None):
    """
    Action for the 'rm' builder. Removes files and directories.

    This function mimics the behavior of the `rm` command-line utility.

    It expects:
      - One or more arguments to be removed:
          - If the argument does not exists -> KO, but continue for others
          - If the argument is a file and exists -> Ok, remove it
          - If the argument is a dir and exists -> Ok, but only if the recursive flag is set

    Args:
        deps: Unused dependencies argument.
        targets: List of files/directories to remove.
        _: Unused console object.
        recursive (bool, optional): If True, allows recursive directory removal (like `rm -r`).
                                    Defaults to None.
    """
    for target in targets:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
        else:
            pass


# Destructive builder for removing files and directories. See `_rm` for details.
rm = Builder(action=_rm, shouldRebuildFun=_FILE_OPS_rmShouldRebuild, destructive=True)

# ==================================================
# =                 Archives                       =
# ==================================================


def _tar(deps, targets, _, compression=""):
    """
    Action for the 'tar' builder. Creates a tar archive.

    Args:
        deps: List of files/directories to add to the archive.
        targets: List containing the path to the output tar file.
        _: Unused console object.
        compression (str, optional): Compression mode ("gz", "bz2", "xz").
                                     Defaults to "".
    """
    cwd = os.getcwd()
    mode = f"w:{compression}" if compression in ("gz", "bz2", "xz") else "w"
    with tarfile.open(targets[0], mode, encoding="utf-8") as tar:
        for dep in deps:
            tar.add(dep.relative_to(cwd))


# Builder for creating tar archives. See `_tar` for details.
tar = Builder(action=_tar)


def _zip(deps, targets, _):
    """
    Action for the 'zip' builder. Creates a zip archive.

    Args:
        deps: List of files/directories to add to the archive.
        targets: List containing the path to the output zip file.
        _: Unused console object.
    """
    cwd = os.getcwd()
    with zipfile.ZipFile(targets[0], "w") as zip:
        for dep in deps:
            if dep.is_dir():
                files = list(dep.rglob("*"))
                for file in files:
                    zip.write(file.relative_to(cwd))
            else:
                zip.write(dep.relative_to(cwd))


# Builder for creating zip archives. See `_zip` for details.
zip = Builder(action=_zip)

# ==================================================
# =              LaTeX Builders                    =
# ==================================================


def _tex2pdf(deps, _, _2, cmd="pdflatex"):
    """
    Action for the 'tex2pdf' builder. Compiles a LaTeX file into a PDF.

    This builder runs pdflatex and bibtex multiple times to ensure all
    references and citations are correctly resolved.

    Args:
        deps: List containing the source .tex file.
        _: Unused targets argument.
        _2: Unused console object.
        cmd (str, optional): The LaTeX command to use (e.g., "pdflatex", "lualatex").
                             Defaults to "pdflatex".
    """
    latexFile = deps[0].replace(".tex", "")
    subprocess.run([cmd, latexFile], check=True)
    subprocess.run(["bibtex", latexFile], check=True)
    subprocess.run([cmd, latexFile], check=True)
    subprocess.run([cmd, latexFile], check=True)


# Builder for compiling LaTeX files to PDF. See `_tex2pdf` for details.
tex2pdf = Builder(action=_tex2pdf)

# ==================================================
# =                C Builders                      =
# ==================================================


def _gcc(_, targets, _2, cflags=""):
    """
    Action for the 'gcc' builder. Compiles C/C++ code using GCC.

    Note: Dependencies are expected to be passed via the cflags.

    Args:
        _: Unused dependencies argument.
        targets: List containing the output executable path.
        _2: Unused console object.
        cflags (str, optional): A string of compiler flags (e.g., "-Wall").
                                Defaults to "".
    """
    subprocess.run(["gcc", cflags, "-o", targets[0]], check=True)


# Builder for compiling with GCC. See `_gcc` for details.
gcc = Builder(action=_gcc)


def _clang(_, targets, _2, cflags=""):
    """
    Action for the 'clang' builder. Compiles C/C++ code using Clang.

    Note: Dependencies are expected to be passed via the cflags.

    Args:
        _: Unused dependencies argument.
        targets: List containing the output executable path.
        _2: Unused console object.
        cflags (str, optional): A string of compiler flags (e.g., "-Wall").
                                Defaults to "".
    """
    subprocess.run(["clang", cflags, "-o", targets[0]], check=True)


# Builder for compiling with Clang. See `_clang` for details.
clang = Builder(action=_clang)

# ==================================================
# =              Other Builders                    =
# ==================================================

# Builder to convert HTML files to PDF using Google Chrome.
html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
# Builder to convert Markdown files to HTML using Pandoc.
md2html = Builder(action="pandoc $^ -o $@")
# Builder to render Jinja2 templates.
jinja2 = Builder(action="jinja2 $^ -o $@")
# Builder to crop PDF files to a single page using pdftk.
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")
