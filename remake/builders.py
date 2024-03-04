#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default builders for ReMake."""

import shutil
import subprocess

from remake.main import Builder

# ==================================================
# =              File Operations                   =
# ==================================================


# Expects either 2 arguments (source, destination),
# or multiple arguments where all be last are source
# and last is the destination directory.
def _cp(deps, targets, _):
    # print(deps, targets)
    assert len(targets) == 1
    for dep in deps:
        if dep.is_file():
            shutil.copy(dep, targets[0], follow_symlinks=False)
        elif dep.is_dir():
            shutil.copytree(dep, targets[0] / dep.name)


cp = Builder(action=_cp)


def _mv(deps, targets, _):
    raise NotImplementedError


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
