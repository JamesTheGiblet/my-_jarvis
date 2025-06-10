# evaluation_harness/ciq_benchmarks/sum_two_numbers/tests.py
import unittest
import sys
import os

# This allows importing 'generated_solution' from the current directory
# The evaluate_ciq.py script will place the AI-generated code in a file
# named 'generated_solution.py' in this directory before running the tests.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SOLUTION_FILE_NAME = "generated_solution"

try:
    # Attempt to import the solve function from the generated solution
    module = __import__(SOLUTION_FILE_NAME)
    solve = getattr(module, "solve")
    SOLUTION_FOUND = True
except (ImportError, AttributeError) as e:
    # print(f"Debug: Could not import solve function: {e}")
    SOLUTION_FOUND = False
    solve = None # Define solve as None if not found

class TestSumTwoNumbers(unittest.TestCase):
    def test_solution_exists_and_callable(self):
        self.assertTrue(SOLUTION_FOUND, f"{SOLUTION_FILE_NAME}.py or solve function not found or not callable.")
        self.assertTrue(callable(solve), "The 'solve' attribute is not callable.")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_positive_numbers(self):
        self.assertEqual(solve(2, 3), 5, "Test with positive numbers failed.")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_negative_numbers(self):
        self.assertEqual(solve(-1, -5), -6, "Test with negative numbers failed.")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_mixed_numbers(self):
        self.assertEqual(solve(10, -3), 7, "Test with mixed numbers failed.")

    @unittest.skipIf(not SOLUTION_FOUND or not callable(solve), "Skipping functional tests because solution was not found or not callable.")
    def test_zero(self):
        self.assertEqual(solve(0, 0), 0, "Test with zeros failed.")
        self.assertEqual(solve(5, 0), 5, "Test with one zero failed.")

if __name__ == '__main__':
    unittest.main()