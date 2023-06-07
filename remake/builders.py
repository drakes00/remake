#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Module implementing builders to be used in rules."""


class Builder():
    """Generic builder class."""
    _action = None

    def __init__(self, action):
        self._action = action

    def parseAction(self, deps, target):
        """Parses builder action for automatic variables ($@, etc)."""
        if isinstance(self._action, str):
            ret = self._action
            if deps:
                ret = ret.replace("$<", " ".join(deps))
                ret = ret.replace("$^", deps[0])
            ret = ret.replace("$@", target)
            ret = ret.split(" ")
            return ret

        return self._action

    @property
    def action(self):
        """Returns builder's action."""
        return self._action


html2pdf_chrome = Builder(
    action="google-chrome-stable --headless --disable-gpu --run-all-compositor-stages-before-draw --print-to-pdf=$@ $^",
)
md2html = Builder(action="pandoc $^ -o $@")
jinja2 = Builder(action="jinja2 $^ -o $@")
pdfcrop = Builder(action="pdftk $^ cat 1 output $@")
