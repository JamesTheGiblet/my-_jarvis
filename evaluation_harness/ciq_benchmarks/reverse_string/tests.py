# evaluation_harness/ciq_benchmarks/reverse_string/tests.py
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SOLUTION_FILE_NAME = "generated_solution"

try:
    module = __import__(SOLUTION_FILE_NAME)
    solve = getattr(module, "solve")
    SOLUTION_FOUND = True
except (ImportError, AttributeError):
    SOLUTION_FOUND = False
    solve = None

class TestReverseString(unittest.TestCase):
    def test_solution_exists_and_callable(self):
        self.assertTrue(SOLUTION_FOUND, f"{SOLUTION_FILE_NAME}.py or solve function not found or not callable.")
        self.assertTrue(callable(solve), "The 'solve' attribute is not callable.")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_simple_string(self):
        self.assertEqual(solve("hello"), "olleh")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_empty_string(self):
        self.assertEqual(solve(""), "")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_palindrome(self):
        self.assertEqual(solve("madam"), "madam")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_string_with_spaces(self):
        self.assertEqual(solve("hello world"), "dlrow olleh")

if __name__ == '__main__':
    unittest.main()