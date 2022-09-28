import datetime
import unittest

from pathlib import Path

from .helpers import replaceTextnumberWithNumber, find_common_prefix, DotDict, get_ebook_name_from_list_of_posts


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

'''

def find_common_prefix(a, b):
	shortest = a if len(a) < len(b) else b
	ret = ''

	for i in range(len(shortest)):
		if a[i].lower() == b[i].lower():
			ret += a[i]
		else:
			break

	if len(ret) == 0:
		print(colorize('# find_common_prefix failed', fg='red'))
		raise ValueError('No common prefix')

	print(f'find_common_prefix: {ret}')
	return f'{ret} - 1337'

'''

class TestFindCommonPrefix(unittest.TestCase):
	def test_has_common(self):
		self.assertEqual(find_common_prefix('aa', 'aa'), 'aa')
		self.assertEqual(find_common_prefix('aa', 'ab'), 'a')
		self.assertEqual(find_common_prefix('aaa', 'aaaaaaaaa'), 'aaa')

	def test_no_common(self):
		with self.assertRaises(ValueError):
			find_common_prefix('a', 'b')

def fake_post_maker(title, when):
	return DotDict({
		'title': title,
		'author': DotDict({'name': '# N/A #'}),
		'created_utc': datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S").timestamp(),
	})

class TestGetEbookNameFromListOfPosts(unittest.TestCase):
	# No number in both names, pick older post as final name
	def test_no_number(self):
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa', '2022-06-20 19:00:00'),
				fake_post_maker('ab', '2022-06-20 20:00:00'),
			]),
			'aa'
		)
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa', '2022-06-20 20:00:00'),
				fake_post_maker('ab', '2022-06-20 19:00:00'),
			]),
			'ab'
		)

	# Number in post names give us a range to work with
	def test_number(self):
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa 1', '2022-06-20 19:00:00'),
				fake_post_maker('ab 2', '2022-06-20 20:00:00'),
			]),
			'a - 1-2'
		)
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa - 10', '2022-06-20 19:00:00'),
				fake_post_maker('aa - 11', '2022-06-20 20:00:00'),
			]),
			'aa - 10-11'
		)
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('Abcd, Ch. 19', '2022-06-20 19:00:00'),
				fake_post_maker('Abcd, Ch. 21', '2022-06-20 20:00:00'),
			]),
			'Abcd, Ch. - 19-21'
		)
		# Result range always from min to max
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa 1', '2022-06-20 20:00:00'),
				fake_post_maker('ab 2', '2022-06-20 19:00:00'),
			]),
			'a - 1-2'
		)
		# Result range always from min to max
		self.assertEqual(
			get_ebook_name_from_list_of_posts([
				fake_post_maker('aa 1', '2022-06-20 12:00:00'),
				fake_post_maker('ab 2', '2022-06-20 13:00:00'),
				fake_post_maker('ab 3', '2022-06-20 14:00:00'),
			]),
			'a - 1-3'
		)

if __name__ == '__main__':
	unittest.main()
