import unittest

# import our test modules
from . import test_brain
from . import test_commands
from . import test_tokenizers

__all__ = ["cobe_suite"]

cobe_suite = unittest.TestSuite()
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_brain))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tokenizers))
