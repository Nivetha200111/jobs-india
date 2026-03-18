import unittest

from jobs_india.validate import validate_outputs


class ValidateOutputsTest(unittest.TestCase):
    def test_repository_outputs_are_production_ready(self):
        self.assertEqual(validate_outputs(), [])
