#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default builders for ReMake."""

import shutil
import subprocess

from remake.main import Builder

# ==================================================
# =              File Operations                   =
# ==================================================


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
    print(deps, targets)
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


cp = Builder(action=_cp)


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


mv = Builder(action=_mv)


def _rm(deps, targets, _):
    raise NotImplementedError


rm = Builder(action=_rm)


def _tar(deps, targets, _):
    raise NotImplementedError


tar = Builder(action=_tar)

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
