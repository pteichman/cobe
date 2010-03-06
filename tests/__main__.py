import unittest

# import our test modules
import test_commands
import test_halng
import test_tokenizer

halng_suite = unittest.TestSuite()
halng_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands))
halng_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_halng))
halng_suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_tokenizer))

runner = unittest.TextTestRunner()
runner.run(halng_suite)
