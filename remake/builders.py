#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Default builders for ReMake."""

from remake.main import Builder

html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
md2html = Builder(action="pandoc $^ -o $@")
jinja2 = Builder(action="jinja2 $^ -o $@")
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")
