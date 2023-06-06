#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Builder(object):
    _action = None

    def __init__(self, action):
        self._action = action

    def _parseAction(self, deps, target):
        if isinstance(self._action, str):
            ret = self._action
            ret = ret.replace("$<", " ".join(deps))
            ret = ret.replace("$^", deps[0])
            ret = ret.replace("$@", target)
            ret = ret.split(" ")
            return ret
        else:
            return self._action

    @property
    def action(self):
        return self._action


html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
md2html = Builder(action="pandoc $^ -o $@")
jinja2 = Builder(action="jinja2 $^ -o $@")
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")
