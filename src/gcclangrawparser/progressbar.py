#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from multiprocessing import Pool

from atpbar import find_reporter, register_reporter
from atpbar.main import Atpbar
from atpbar.funcs import flush, disable


# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_LOGGER = logging.getLogger(__name__)


## ==================================================


def disable_progressar():
    disable()


def end_progressbar():
    reporter = find_reporter()
    if reporter is None:
        # happens when progress bar is disabled
        return
    reporter.end_pickup()


def iterate_progressar(container, progress_name, container_len):
    return Atpbar(container, progress_name, container_len)


## ==================================================


def get_processbar_pool(pool_class, *args, **kwargs):
    return MultiprocessProcessBar(pool_class, *args, **kwargs)


class MultiprocessProcessBar:
    def __init__(self, pool_class, *args, **kwargs):
        if pool_class is None:
            pool_class = Pool
        self.pool = pool_class(
            *args,
            **kwargs,
            initializer=register_reporter,
            initargs=(find_reporter(),),
        )

    def __enter__(self):
        return self.pool.__enter__()

    def __exit__(self, obj_type, value, traceback):
        self.pool.__exit__(obj_type, value, traceback)
        flush()


## ==================================================


#
# Example:
#    name = "job"
#    with get_single_stepper_context(name, data_list) as progress:
#        for item in data_list:
#            progress.step()
#            ## process item
#
def get_single_stepper_context(name, container):
    container_size = len(container)
    return AtpbarContext(name, container_size)


class AtpbarContext:
    def __init__(self, name, steps_num):
        self.stepper = AtpbarStepper(name, steps_num)

    def __enter__(self):
        self.stepper.start()
        return self.stepper

    def __exit__(self, _type, _value, _traceback):
        self.stepper.end()


class AtpbarStepper:
    def __init__(self, name, steps_num):
        self.progress = Atpbar([], name, steps_num)
        self.progress.reporter = find_reporter()

    def start(self):
        self.progress.loop_complete = False
        self.progress._report_start()  # pylint: disable=W0212

    def step(self):
        self.progress._done += 1
        self.progress._report_progress()  # pylint: disable=W0212

    def end(self):
        with self.progress._report_last():  # pylint: disable=W0212
            pass
        self.progress.reporter.end_pickup()
        self.progress.loop_complete = True
        flush()
