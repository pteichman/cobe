import unittest

# import our test modules
import test_commands
import test_cobe
import test_tokenizer

__all__ = ["cobe_suite"]

cobe_suite = unittest.TestSuite()
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_cobe))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tokenizer))
