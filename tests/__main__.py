import unittest

# import our test modules
import test_commands
import test_cobe
import test_tokenizer

cobe_suite = unittest.TestSuite()
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_cobe))
cobe_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tokenizer))

runner = unittest.TextTestRunner()
runner.run(cobe_suite)
