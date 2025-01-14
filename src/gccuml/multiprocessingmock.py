#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#


class ResultObject:
    def __init__(self, result):
        self.result = result

    def get(self):
        return self.result


# single threaded pool with multiprocessing.Pool interface
class DummyPool:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):  # pylint: disable=W0622
        pass

    def apply_async(self, func, args=()):
        return ResultObject(func(*args))

    def starmap(self, func, iterable=()):
        for args in iterable:
            func(*args)
