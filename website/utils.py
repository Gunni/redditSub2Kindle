import datetime
import io
import logging
import operator
import os
import pickle
import re
import string
import time
from collections import defaultdict
from contextlib import contextmanager
from subprocess import Popen, PIPE
import tempfile
import textwrap

import praw
from PIL import ImageFont

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.utils.termcolors import colorize
from django.http import HttpResponse
from prawcore import Forbidden

from ebooklib import epub

from .helpers import replaceTextnumberWithNumber
from .models import Story

logger = logging.getLogger(__name__)

from django.core.cache import cache

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
# BUG: if an ANCIENT post is pinned (100+ posts ago), it will still appear in the first 100 post list
#      idea is to hold back really old pinned posts until we get an unpinned one that's older
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
					print('IT CAN HAPPEN!')

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
				post = get_or_set_cache(next(self.iterator), None)
				post.__hash__ = hash(post.id)

				posts.append(post)

				if self.iterator._listing is None or (self.iterator._list_index + 1) > len(self.iterator._listing):
					break
		except Forbidden as e:
			print(f'Got HTTP Forbidden while getting {self.iterator.url}, either he/she or we have been banned, please check and or remove')
			raise e
		except StopIteration:
			done = True

		return {'posts': sort_posts(posts), 'done': done}

def get_story(iterator, subscription, how_many_liked_i_want):
	print(f'get_story {colorize(subscription, fg="green")} liked? {how_many_liked_i_want}')

	results = set()
	upvoted = 0

	for post in iterator:
		# deleted posts are ignored like this, there is no deleted bool that I found
		if post.removed_by_category is not None:
			continue

		if post.subreddit != subscription.subreddit:
			continue

		title = subscription.title_fragment

		if not subscription.is_regex:
			title = re.escape(title)

		r = re.search(title, post.title, re.IGNORECASE)
		if r is None:
			continue

		# if we got to this point, then this post is acceptable!
		# if it is already in an upvoted state, count it, otherwise add it without counting it

		post.fixed_title = fix_title(post)
		post.upvotable = can_upvote(post)

		if post.likes == True or post.hidden:
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

	# no subs means no results, bail early on this author
	if len(subscriptions) == 0:
		print(f'FYI: {author} has no enabled subscriptions')
		return results

	iterator = PostIterator(reddit.redditor(author.username).submissions.new(limit=None))

	for subscription in subscriptions:
		results.update(get_story(iterator, subscription, how_many_likes_i_want))
		print(f'iterator storage size: {len(iterator.storage)}')

	return sort_posts(results)

def sort_posts(posts):
	return sorted(posts, reverse=True, key=operator.attrgetter('created_utc'))

def fix_title(post):
	dt = datetime.datetime.fromtimestamp(post.created_utc)

	# Nuke unicode
	printable = set(string.printable)
	common_name = ''.join(filter(lambda x: x in printable, post.title))

	common_name = replaceTextnumberWithNumber(common_name).strip('.')
	common_name = re.sub(r'(.*)Tales From the Terran Republic(.*)', rf'TFtTR {dt:%Y-%m-%dT%H%M} - \1 \2', common_name, flags=re.IGNORECASE)
	common_name = re.sub(r'\[OP\]', ' ', common_name)
	common_name = re.sub(r'[\[\]]', ' ', common_name)
	common_name = re.sub(r' +', ' ', common_name)
	common_name = re.sub(r'Story Continuation', '', common_name)
	common_name = re.sub(r'^ Serial ', '', common_name)

	if post.author.name == 'Ralts_Bloodthorne' and 'Chapter' in common_name[:7]:
		common_name = f'First Contact - {common_name}'

	return common_name

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

def download_ebook_with_comments(post_id, index=None):
	reddit = praw.Reddit()
	post = reddit.submission(post_id)

	dt = datetime.datetime.fromtimestamp(post.created_utc)

	common_name = fix_title(post)

	filename = re.sub(r':', ' ', common_name)
	filename = re.sub(r'/', ' ', filename)
	filename = re.sub(r'’', ' ', filename)

	filename = f'{filename[:96]}.azw3'

	post.comment_sort = 'best'
	post.comment_limit = 10
	post.comments.replace_more(limit=0)

	book = epub.EpubBook()
	book.set_title(common_name)
	book.add_author(str(post.author))
	book.set_language('en')

	html = f'<div id="title">\n'
	html += f'<h1><a href="{post.url}">{common_name}</a></h1>\n'
	html += f'<h2>by {post.author}</h2>\n'
	html += f'<h3>at {dt:%Y-%m-%d %H:%M:%S}</h3>\n'
	html += f'</div>\n'

	html += f'<hr />\n'

	if post.selftext_html is not None:
		html += post.selftext_html
	else:
		html += '<p>## Post has no selftext_html ##</p>'

	html = re.sub(r'www.reddit.com', 'i.reddit.com', html)

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

	# create chapter
	chapter = epub.EpubHtml(title='Post Body', file_name='a.html', lang='en')
	chapter.content = html
	chapter.add_link(href='styles.css', rel='stylesheet', type='text/css')

	comments = epub.EpubHtml(title='Comments', file_name='b.html', lang='en')
	comments.content = getCommentForestHTML(post, post.comments)
	comments.add_link(href='styles.css', rel='stylesheet', type='text/css')

	# add chapter
	book.add_item(css)
	book.add_item(chapter)
	book.add_item(comments)

	# define Table Of Contents
	book.toc = (chapter, comments)
	# add chapter listing thingy (allows readers that support it to list chapters)
	book.add_item(epub.EpubNcx())

	# basic spine
	book.spine = [ chapter, comments ]

	response = None

	# write to the file
	with my_named_temporary_file(prefix='redditSub2KindleTMP-', suffix='.epub') as f1:
		epub.write_epub(f1, book, {})

		# Close the file so that ebook-convert can mess with it
		f1.close() # https://bugs.python.org/issue14243

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

def getCommentForestHTML(post, forest, level=0) -> str:
	ret = ''

	for comment in forest:
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
		authorflag = '<strong>(OP)</strong> ' if post.author == comment.author else ''

		indent = '\t' * level

		ret += f'{indent}<hr /><blockquote>\n'
		ret += f'{indent}\t<h3>{authorflag}<strong>/u/{comment.author}</strong></h3>'
		ret += f'{indent}\t<h4>at {dt} (d:{level + 1})</h4>\n'
		body = comment.body_html

		# users adding their own hr confuses the user
		body = re.sub(r'<hr ?/?>', '-' * 20, body)

		indented_body = textwrap.indent(body, f'{indent}\t')
		ret += f'{indented_body}\n\n'

		ret += textwrap.indent(getCommentForestHTML(post, comment.replies, level+1), indent)

		ret += f'{indent}</blockquote>\n'

	return ret


# I use upvote to "mark as read" but reddit annoyingly prevents upvoting after
# 6 months, so this returns false for those, since i can then hide them instead
def can_upvote(post):
	posted_at = datetime.datetime.fromtimestamp(int(post.created_utc)).replace(hour=0, minute=0, second=0)
	max_age = datetime.datetime.today() + relativedelta(months=-6)

	return posted_at > max_age
