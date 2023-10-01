#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default builders for ReMake."""

import subprocess

from remake.main import Builder

# ==================================================
# =              LaTeX Builders                    =
# ==================================================


def _tex2pdf(deps, _, _2, cmd="pdflatex"):
    latexFile = deps[0].replace(".tex", "")
    subprocess.run([cmd, latexFile])
    subprocess.run(["bibtex", latexFile])
    subprocess.run([cmd, latexFile])
    subprocess.run([cmd, latexFile])


tex2pdf = Builder(action=_tex2pdf)

# ==================================================
# =                C Builders                      =
# ==================================================


def _gcc(deps, targets, _2, cflags=""):
    subprocess.run(["gcc", cflags, "-o", targets[0]])


gcc = Builder(action=_gcc)


def _clang(deps, targets, _2, cflags=""):
    subprocess.run(["clang", cflags, "-o", targets[0]])


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
