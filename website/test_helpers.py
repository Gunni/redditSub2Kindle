import unittest

from pathlib import Path

from .helpers import replaceTextnumberWithNumber


class TestReplaceTextnumberWithNumber(unittest.TestCase):
	def test_number(self):
		self.assertEqual(replaceTextnumberWithNumber('four'), '4')

	def test_number_in_a_sentence(self):
		self.assertEqual(replaceTextnumberWithNumber('There were forty two of them'), 'There were 42 of them')

	def test_multiple_numbers_in_a_sentence(self):
		self.assertEqual(replaceTextnumberWithNumber(
			'Example Chapter Title: Chapter Twenty (End of Book One)'
		), 'Example Chapter Title: Chapter 20 (End of Book 1)')

	def test_table(self):
		with open(Path(__file__).parent / Path('test_helpers.table'), 'r') as f:
			for line in f:
				try:
					before, after = map(str.strip, line.split(';'))
					self.assertEqual(replaceTextnumberWithNumber(before), after)
				except ValueError as e:
					print(line)
					print(e)

if __name__ == '__main__':
	unittest.main()
