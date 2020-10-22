#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pickle
import pprint
import configparser

cwd = os.path.dirname(__file__)
config = configparser.ConfigParser(interpolation=None)
config.read(os.path.join(cwd, "knxcal.ini"))

with open(os.path.join(cwd, config["knxcal"]["stateFile"]), "rb") as f:
    try:
        state = pickle.load(f)
    except EOFError:
        state = {}

pprint.pprint(state)
