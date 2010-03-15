import unittest

# import our test modules
import test_brain
import test_commands
import test_tokenizers

__all__ = ["cobe_suite"]

cobe_suite = unittest.TestSuite()
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_brain))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tokenizers))
