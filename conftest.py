"""Pins the local timezone: doctests and tests print local times"""

import os
import time

os.environ["TZ"] = "Europe/Berlin"
time.tzset()
