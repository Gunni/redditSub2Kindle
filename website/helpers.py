import datetime
import operator
import re
import string

import nltk as nltk
from word2number import w2n
from django.utils.termcolors import colorize

# Takes in string containing "numberwords" and returns it with those "numberwords" replaced with digits
# Examples:
# 'Hello one two three' becomes 'Hello 123'
def replaceTextnumberWithNumber(text):
	# Exceptions:
	if len(text) > 10 and 'Seven Days of Fire' in text:
		return text

	tagged_number_words = 'ten/CD thousand/CD nine/CD hundred/CD ninety/CD eight/CD seven/CD six/CD five/CD four/CD three/CD two/CD one/CD eighty/CD seventy/CD sixty/CD fifty/CD forty/CD thirty/CD twenty/CD nineteen/CD eighteen/CD seventeen/CD sixteen/CD fifteen/CD fourteen/CD thirteen/CD twelve/CD eleven/CD zero/CD'
	tagged_number_words_tuples = [nltk.tag.str2tuple(t) for t in tagged_number_words.split()]
	my_tagger = nltk.UnigramTagger([ tagged_number_words_tuples ], backoff=nltk.DefaultTagger('IGNORE'))

	my_grammar = 'NumberWord: {<CD>+}'
	parser = nltk.RegexpParser(my_grammar)
	parsed = parser.parse(my_tagger.tag(nltk.word_tokenize(text.lower())))

	for tag in [tree.leaves() for tree in parsed.subtrees() if tree.label() == 'NumberWord']:
		ut = nltk.untag(tag)
		num = w2n.word_to_num(' '.join(ut))

		r = re.compile(re.escape(' '.join(ut)), re.IGNORECASE)
		text = r.sub(str(num), text)

	return text


class DotDict(dict):
	"""dot.notation access to dictionary attributes"""
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__


def sort_posts(posts):
	return sorted(posts, reverse=True, key=operator.attrgetter('created_utc'))


# noinspection RegExpRedundantEscape
def standardize_title(post):
	dt = datetime.datetime.fromtimestamp(post.created_utc)

	# Nuke unicode
	printable = set(string.printable)
	common_name = ''.join(filter(lambda x: x in printable, post.title))

	common_name = replaceTextnumberWithNumber(common_name).strip('.')
	common_name = re.sub(r'(.*)Tales From the Terran Republic(.*)', rf'TFtTR {dt:%Y-%m-%dT%H%M} - \1 \2', common_name, flags=re.IGNORECASE)
	common_name = re.sub(r'\[OP\]', ' ', common_name)
	common_name = re.sub(r'\[OC\]', ' ', common_name)
	common_name = re.sub(r'[\[\]]', ' ', common_name)
	common_name = re.sub(r' +', ' ', common_name)
	common_name = re.sub(r'Story Continuation', '', common_name)
	common_name = re.sub(r'^ Serial ', '', common_name)

	if post.author.name == 'Ralts_Bloodthorne' and 'Chapter' in common_name[:7]:
		common_name = f'First Contact - {common_name}'

	# He stopped numbering his posts on 2022-01-10, and therefore I started adding datestamps
	# Sometimes this absolute mad lad posts multiple times per hour, so that's the that is required
	if post.author.name == 'Ralts_Bloodthorne' and 'First Contact' in common_name[:13]:
		common_name = common_name.replace('First Contact', f'FC - {dt:%Y%m%dT%H%M}')

	if post.author.name == 'Tigra21' and len(common_name) > 3 and common_name[:3] == 'HoH':
		common_name = common_name.replace('HoH', 'Hunter or Huntress')

	return common_name


def generate_filename_for_post(post, extension='azw3'):
	common_name = standardize_title(post)

	filename = re.sub(r':', ' ', common_name)
	filename = re.sub(r'/', ' ', filename)
	filename = re.sub(r'’', ' ', filename)
	filename = re.sub(r',', ' ', filename)
	filename = re.sub(r'\?', ' ', filename)
	filename = f'{filename[:96].strip()}.{extension}'

	return filename


# Takes in two strings and returns the shortest common string from the start until they diverge
# Examples:
# 'aa', 'ab' returns 'a'
def find_common_prefix(a, b):
	shortest = a if len(a) < len(b) else b
	ret = ''

	for i in range(len(shortest)):
		if a[i].lower() == b[i].lower():
			ret += a[i]
		else:
			break

	if len(ret) == 0:
		raise ValueError('No common prefix')

	#print(f'find_common_prefix: {ret}')
	return f'{ret}'

def get_ebook_name_from_list_of_posts_first_contact(first, last):
	first_matches = re.match(r'^FC - (?P<ts>[0-9T]+)(?: - Chapter ([0-9]+))?', first.fixed_title)
	last_matches = re.match(r'^FC - (?P<ts>[0-9T]+)(?: - Chapter ([0-9]+))?', last.fixed_title)

	if first_matches is None or last_matches is None:
		print(f'Regex failed for either "{first.fixed_title}" or "{last.fixed_title}"')
		return first.fixed_title

	missingno = 'XXX'

	new_title = f'FC - {first_matches.group(1)}-{last_matches.group(1)} '
	new_title += f'({first_matches.group(2)}-' if first_matches.group(2) is not None else f'({missingno}-'
	new_title += f'{last_matches.group(2)})' if last_matches.group(2) is not None else f'{missingno})'

	print(f'NEW TITLE: {new_title}')

	return new_title

def get_ebook_name_from_list_of_posts(posts):
	# This function needs posts to be in time order
	posts = list(reversed(sort_posts(posts.copy())))

	for post in posts:
		post.fixed_title = standardize_title(post)

	if len(posts) == 0:
		raise Exception('called with an empty list')
	elif len(posts) == 1:
		return posts[0].fixed_title

	first = posts[0]
	last = posts[-1]

	number_regex = re.compile(r'([0-9]+(?:[0-9\.]+)?)')

	first_n = number_regex.findall(first.fixed_title)
	last_n = number_regex.findall(last.fixed_title)

	# First Contact has an annoying chapter name sometimes, so we handle it in a special way...
	if first.fixed_title[0:2] == 'FC' and last.fixed_title[0:2] == 'FC':
		return get_ebook_name_from_list_of_posts_first_contact(first, last)

	# There are no results, or too many results
	if len(first_n) != 1 or len(last_n) != 1:
		return first.fixed_title

	first_res = first_n[0]
	last_res = last_n[0]

	if len(first_n) == 0 or len(last_n) == 0:  # No numbers found
		return first.fixed_title
	elif len(first_n) > 1 or len(last_n) > 1:  # Too many numbers found, use last number
		first_res = first_n[-1]
		last_res = last_n[-1]

	# If we get here, we have a viable range
	n = [ 0, 0 ]

	def x(n):
		try:
			return int(n)
		except ValueError:
			return float(n)

	n[0] = x(first_res)
	n[1] = x(last_res)

	# Try a common prefix method
	try:
		r = find_common_prefix(first.fixed_title, last.fixed_title)
		r = re.sub(r'\d+', '', r) # Strip any numbers out of the common prefix (prevents 31 and 32 leaving 3)
		r = re.sub(r' - $|#$|\($', '', r) # Strip any trailing separators
		r = r.strip() # Strip any trailing separators
		r += f' - {min(n)}-{max(n)}' # add the chapter range
	except ValueError:
		r = re.sub(number_regex, f'{min(n)}-{max(n)}', first.fixed_title)

	return r
