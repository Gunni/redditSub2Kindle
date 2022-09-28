import datetime
import logging
import os
import pickle
import re

import uuid
from contextlib import contextmanager
from subprocess import Popen, PIPE
import tempfile
import textwrap

import praw

import textile

from dateutil.relativedelta import relativedelta
from django.utils.termcolors import colorize
from django.http import HttpResponse
from prawcore import Forbidden, ResponseException
from fuzzywuzzy import fuzz

from ebooklib import epub

from .helpers import replaceTextnumberWithNumber, sort_posts, generate_filename_for_post, standardize_title, DotDict
from .models import Story

from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_or_set_cache(post, how_long=60 * 60 * 24 * 7):
	c = cache.get(post.id)

	if c is not None:
		c2 = pickle.loads(c)
		return c2

	# make it non-lazy
	_ = post.title

	cache.set(post.id, pickle.dumps(post), how_long)

	return post


# Ensures that when I vote or hide a post, it will be re-downloaded with
# updated flags whenever I reload the page
def wipe_cache(post_id):
	cache.delete(post_id)


# The whole reason this class even exists is because of this issue
# https://www.reddit.com/r/redditdev/comments/oheh52/submissionsnew_returns_pinned_posts_out_of_order/
# We can not request posts in strict time order because pinned posts are always first
# BUG: if an ANCIENT post is pinned (1000+ posts ago), it will still appear in the first 100 post list
#      idea is to hold back ancient pinned posts until we get an unpinned one that's older
class PostIterator:
	def __init__(self, iterator):
		self.iterator = iterator
		self.storage = []
		self.can_get_more = True

	def __iter__(self):
		self.element = -1
		return self

	def __next__(self):
		self.element += 1

		try:
			return self.storage[self.element]
		except IndexError:
			if self.can_get_more:
				batch = self.get_next_batch()
				self.storage.extend(batch['posts'])
				self.can_get_more = not batch['done']

				if batch['done'] and len(batch['posts']) > 0:
					raise Exception('IT CAN HAPPEN!')

				if len(batch['posts']) > 0:
					return self.storage[self.element]
				else:
					raise StopIteration
			else:
				raise StopIteration

	def get_next_batch(self):
		print(colorize(f'requesting page for {self.iterator.url} with {self.iterator.params}', fg='yellow'))
		posts = []
		done = False

		try:
			while True:
				try:
					post = get_or_set_cache(next(self.iterator))
				except ResponseException as e:
					raise e

				post.__hash__ = hash(post.id)

				posts.append(post)

				# noinspection PyProtectedMember
				if self.iterator._listing is None or (self.iterator._list_index + 1) > len(self.iterator._listing):
					break
		except Forbidden as e:
			print(f'Got HTTP Forbidden while getting {self.iterator.url}, either he/she or we have been banned, please check and or remove')
			raise e
		except ResponseException as e:
			print(f'########### {e}')
			raise e
		except StopIteration:
			done = True

		return {'posts': sort_posts(posts), 'done': done}


def get_N_subscription_posts(iterator, subscription, how_many_liked_i_want):
	results = set()
	upvoted = 0

	for post in iterator:
		# deleted posts are ignored like this, there is no deleted bool that I found
		if post.removed_by_category is not None:
			continue

		if post.subreddit != subscription.subreddit:
			continue

		# Title search method
		# non-fuzzy stuff first
		if subscription.is_regex or not subscription.is_fuzzy:
			title = subscription.title_fragment
			if not subscription.is_regex:
				title = re.escape(title)

			r = re.search(title, post.title, re.IGNORECASE)
			if r is None:
				continue
		else:
			# fuzzy stuff
			result = fuzz.partial_ratio(subscription.title_fragment, post.title)

			if result < subscription.fuzzy_ratio:
				continue

		# if we got to this point, then this post is acceptable!
		# if it is already in an upvoted state, count it, otherwise add it without counting it

		post.fixed_title = standardize_title(post)
		post.upvotable = can_upvote(post)

		# What constitutes a post that is read?
		# Upvoted, or Hidden
		post.is_read = post.likes is True or post.hidden

		if post.is_read:
			if upvoted < how_many_liked_i_want:
				upvoted += 1
				results.add(post)
			else:
				break
		else:
			results.add(post)

	return results


def get_reddit_posts(author, story, how_many_likes_i_want=10):
	reddit = praw.Reddit()

	if story is not None:
		subscriptions = [ story ]
	else:
		subscriptions = Story.objects.filter(author=author, enabled=True)

	results = set()

	# no subs, means no results, bail early on this author
	if len(subscriptions) == 0:
		print(f'FYI: {author} has no enabled subscriptions')
		return results

	iterator = PostIterator(reddit.redditor(author.username).submissions.new(limit=None))

	for subscription in subscriptions:
		results.update(get_N_subscription_posts(iterator, subscription, how_many_likes_i_want))

	return sort_posts(results)


def generate_ebook_from_plaintext(title, text):
	t = DotDict({
		'title': title,
		'author': DotDict({'name': '# N/A #'}),
		'created_utc': datetime.datetime.utcnow().timestamp(),
	})

	book = create_empty_book(standardize_title(t), 'N/A')

	# create chapter
	chapter = epub.EpubHtml(title=title, file_name=f'{generate_filename_for_post(t)}.html', lang='en')
	chapter.content = textile.textile(text)
	chapter.add_link(href='styles.css', rel='stylesheet', type='text/css')

	book.add_item(chapter)

	# We have to define a Table Of Contents
	book.toc = (chapter, )
	# add chapter listing thingy (allows readers that support it to list chapters)
	book.add_item(epub.EpubNcx())

	# basic spine
	book.spine = [ chapter ]

	return convert_book_to_epub_azw3_response(
		book,
		generate_filename_for_post(t)
	)


def get_posts_as_ebook(posts, title, author):
	toc = []
	book = create_empty_book(title, author)

	filename = generate_filename_for_post(DotDict({
		'title': title,
		'author': DotDict({'name': author}),
		'created_utc': datetime.datetime.utcnow().timestamp(),
	}))

	for p in posts:
		post = get_or_set_cache(p)
		print(f'Adding "{standardize_title(post)}" to book')

		chapter, comments = post_to_chapter_and_comments(post)

		book.add_item(chapter)
		book.add_item(comments)

		toc.extend([ chapter, comments ])

	# We have to define a Table Of Contents
	book.toc = tuple(toc)
	# add chapter listing thingy (allows readers that support it to list chapters)
	book.add_item(epub.EpubNcx())

	# basic spine
	book.spine = toc

	return convert_book_to_epub_azw3_response(book, filename)



def create_empty_book(title, author):
	book = epub.EpubBook()
	book.set_template('cover', 'test')

	book.set_title(title)
	book.add_author(str(author))
	book.set_language('en')

	# TODO Generate cover?
	#with open('test.svg', 'rb') as f:
	#	book.set_cover('cover.svg', f.read())

	style = 'body {\n' \
			'   text-align: justify;\n' \
			'   text-justify: inter-character;\n' \
			'   hyphens: auto;\n' \
			'   margin: .5em;' \
			'}\n' \
			'\n' \
			'blockquote {\n' \
			'   border-left: 3px solid black;' \
			'   margin-right: 0;\n' \
			'   margin-left: 0.3em;\n' \
			'   padding-left: 0.2em;\n' \
			'}\n' \
			'\n' \
			'#title h1 {\n' \
			'   font-size: 1.5em;\n' \
			'   font-weight: strong;\n' \
			'}\n' \
			'\n' \
			'#title h2 {\n' \
			'   font-size: 1.2em;\n' \
			'   font-weight: normal;\n' \
			'   font-style: oblique;\n' \
			'}\n' \
			'\n' \
			'#title h3 {\n' \
			'   font-size: 1em;\n' \
			'   font-weight: normal;\n' \
			'   font-style: italic;\n' \
			'}\n' \
			'\n' \
			'h3 {\n' \
			'   font-size: 1.1em;\n' \
			'   font-weight: normal;\n' \
			'   font-style: oblique;\n' \
			'}\n' \
			'\n' \
			'h4 {\n' \
			'   font-size: 1em;\n' \
			'   font-weight: normal;\n' \
			'   font-style: italic;\n' \
			'}\n' \

	css = epub.EpubItem(
		file_name="styles.css",
		media_type="text/css",
		content=style
	)

	book.add_item(css)

	return book


def post_to_chapter_and_comments(post):
	dt = datetime.datetime.fromtimestamp(post.created_utc)

	html = f'<div id="title">\n'
	html += f'<h1><a href="{post.url}">{standardize_title(post)}</a></h1>\n'
	html += f'<h2>by {post.author}</h2>\n'
	html += f'<h3>at {dt:%Y-%m-%d %H:%M:%S}</h3>\n'
	html += f'</div>\n'

	html += f'<hr />\n'

	if post.selftext_html is None:
		html += '<p>## Post has no selftext_html ##</p>'
	else:
		html += post.selftext_html

	# replace www.reddit.com with i.reddit.com so that kindle can load it without dying
	html = re.sub(r'www.reddit.com', 'i.reddit.com', html)

	# We use UUID because no two files can have the same filename or the ebook breaks
	filename = uuid.uuid4()

	# create chapter
	chapter = epub.EpubHtml(title=post.title, file_name=f'{filename}.html', lang='en')
	chapter.content = html
	chapter.add_link(href='styles.css', rel='stylesheet', type='text/css')

	# Configure how we get post comments
	post.comment_sort = 'best'
	post.comment_limit = 10
	post.comments.replace_more(limit=0)

	comments = epub.EpubHtml(title=post.title + ' Comments', file_name=f'{filename}.comments.html', lang='en')
	comments.content = get_comment_forest_as_html(post, post.comments)
	comments.add_link(href='styles.css', rel='stylesheet', type='text/css')

	return chapter, comments


# fix for https://bugs.python.org/issue14243
@contextmanager
def my_named_temporary_file(prefix, suffix):
	f = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
	try:
		yield f
	finally:
		try:
			os.unlink(f.name)
		except OSError:
			pass


# This function takes in a `book` object and converts it to epub, which is written to a temp file
# then that temp file is closed, and we use ebook-convert to convert it to azw3 so kindles can read it
# That file then gets returned as file download
def convert_book_to_epub_azw3_response(book, filename):
	with my_named_temporary_file(prefix='redditSub2KindleTMP-', suffix='.epub') as f1:
		epub.write_epub(f1, book, {})

		# Close the file so that ebook-convert can mess with it
		f1.close()  # https://bugs.python.org/issue14243

		process = Popen([ r'C:\\Program Files\\Calibre2\\ebook-convert.exe', f1.name, f'{f1.name}.azw3' ], stdout=PIPE, stderr=PIPE)
		stdout, stderr = process.communicate()

		if len(stderr) > 0:
			raise BrokenPipeError(f'ebook-convert: {stderr.decode("utf-8")}')

		# https://bugs.python.org/issue14243#msg164504
		def temp_opener(name, flag, mode=0o444):
			return os.open(name, flag | os.O_TEMPORARY, mode)

		# f2 should be ready now
		with open(f'{f1.name}.azw3', "rb", opener=temp_opener) as f2:
			# We must respond appropriately for Kindle to prompt the user to download the file to documents
			response = HttpResponse(f2.read(), content_type='application/octet-stream')
			response['Content-Description'] = 'File Transfer'
			response['Content-Disposition'] = f'attachment; filename="{filename}"'

	return response


def get_comment_forest_as_html(post, forest, level=0) -> str:
	ret = ''

	for comment in forest:
		# noinspection PyUnresolvedReferences
		if isinstance(comment, praw.models.MoreComments):
			raise AssertionError('MoreComments happened, despite replace_more?')

		# Ignore common bot comments
		if comment.author in ('HFYWaffle', 'UpdateMeBot', 'HFYBotReborn', 'AutoModerator'):
			continue

		# Ignore useless posts
		if len(comment.body) < 40:
			continue

		# Ignore moderator posts
		if comment.stickied:
			continue

		dt = datetime.datetime.fromtimestamp(comment.created_utc)
		author_flag = '<strong>(OP)</strong> ' if post.author == comment.author else ''

		indent = '\t' * level

		ret += f'{indent}<hr /><blockquote>\n'
		ret += f'{indent}\t<h3>{author_flag}<strong>/u/{comment.author}</strong></h3>'
		ret += f'{indent}\t<h4>at {dt} (d:{level + 1})</h4>\n'
		body = comment.body_html

		# users adding their own hr confuses the user
		body = re.sub(r'<hr ?/?>', '-' * 20, body)

		indented_body = textwrap.indent(body, f'{indent}\t')
		ret += f'{indented_body}\n\n'

		ret += textwrap.indent(get_comment_forest_as_html(post, comment.replies, level + 1), indent)

		ret += f'{indent}</blockquote>\n'

	return ret


# I use upvote to "mark as read" but reddit annoyingly prevents upvoting after
# 6 months, so this returns false for those, since I can then hide them instead
def can_upvote(post):
	# Reddit introduced commenting/upvoting archived posts on 2021-10-01 which makes this check redundant for communities
	# that allow it... But there exists no mechanism to check if a community has it enabled except manual testing...
	# https://www.reddit.com/r/blog/comments/pze6d2/commenting_on_archived_posts_images_in_chat_and/

	# r/HFY has disabled post archiving 2021-10-17
	# https://www.reddit.com/r/HFY/comments/pztdfk/meta_mods_enable_comments_and_votes_on_old_posts/
	if post.subreddit == 'HFY':
		return True

	posted_at = datetime.datetime.fromtimestamp(int(post.created_utc)).replace(hour=0, minute=0, second=0)
	max_age = datetime.datetime.today() + relativedelta(months=-6)

	return posted_at > max_age
