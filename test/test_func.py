#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ward import test


@test("Automatically detect dependencies")
def test_01_funDeps():
    pass

# Meme dépendance dans plusieurs branche
# Pas de cycles
# Nettoyage des deps (make clean)
# Environnement avec dossier cache et output
# Rules must make target
