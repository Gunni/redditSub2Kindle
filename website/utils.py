import datetime
import logging
import operator
import pickle
import pprint
import re
import praw

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
from prawcore import Forbidden

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

	print(f'{post.id} cached: no  {post.title}')

	cache.set(post.id, pickle.dumps(post), how_long)

	return post

def wipe_cache(post_id):
	cache.delete(post_id)

	print(f'{post_id} erased from cache')

# Get N posts by author where N is all unupvoted posts until i get
# `how_many_likes_i_want` upvoted posts
def get_posts_by_sub(author, story, how_many_likes_i_want=1):
	reddit = praw.Reddit()

	returned_posts = set()

	how_many_likes_do_we_have_already = 0

	if story is not None:
		subscriptions = [ story ]
	else:
		subscriptions = Story.objects.filter(author=author, enabled=True)

	try:
		for post in reddit.redditor(author.username).submissions.new(limit=None):
			post = get_or_set_cache(post, None)

			acceptedSub = False

			for subscription in subscriptions:
				acceptedSub |= (post.subreddit == subscription.subreddit)

			if not acceptedSub:
				continue

			if post.pinned:
				continue

			if post.removed_by_category is not None:
				print(f'"{post.title}" is deleted?')

			acceptedPost = False

			for subscription in subscriptions:
				# Ensure we skip posts not matching regex
				r = re.match(rf'.*{re.escape(subscription.title_fragment)}.*', post.title, re.IGNORECASE)
				acceptedPost |= True if r is not None else False

			if not acceptedPost:
				continue

			if post.likes or post.hidden:
				if how_many_likes_do_we_have_already >= how_many_likes_i_want:
					break

				how_many_likes_do_we_have_already += 1

			post.upvotable = can_upvote(post)
			post.author = author
			post.story = story

			returned_posts.add(post)
	except Forbidden:
		print(f'Got HTTP Forbidden while getting {author.username}, either he/she or we have been banned, please check and or remove')

	return sort_posts(returned_posts)

def sort_posts(posts):
	return sorted(posts, reverse=True, key=operator.attrgetter('created_utc'))

def downloadPostWithComments(post_id):
	reddit = praw.Reddit()
	post = reddit.submission(post_id)

	text = ''
	if post.selftext_html is not None:
		soup = BeautifulSoup(post.selftext_html, features='html.parser')
		text = soup.get_text()

	dt = datetime.datetime.fromtimestamp(post.created_utc)
	text = f'# {post.title}\n# Posted by /u/{post.author} to /r/{post.subreddit} at {dt}\n\n{text}'
	text = re.sub(r'\n__+\n', '\n--- --- --- --- --- --- --- ---\n', text)

	text = text.strip()

	filename = replaceTextnumberWithNumber(post.title).strip('.')
	filename = re.sub(r':', ' ', filename)
	filename = re.sub(r'’', '', filename)
	filename = f'{filename[:100]}.txt'
	print(filename)

	text += '\n----------\nComments:'

	post.comment_sort = 'best'
	post.comment_limit = 10

	n = 0
	for comment in post.comments:
		if isinstance(comment, praw.models.MoreComments):
			continue

		if comment.author in ('HFYWaffle', 'UpdateMeBot', 'HFYBotReborn'):
			continue

		if len(comment.body) < 30:
			continue

		n += 1
		dt = datetime.datetime.fromtimestamp(comment.created_utc)
		text += f'\n{n}. /u/{comment.author} at {dt}\n{comment.body}\n---'

	response = HttpResponse(text, content_type='application/octet-stream')
	response['Content-Description'] = 'File Transfer'
	response['Content-Disposition'] = f'attachment; filename="{filename}"'

	return response

# I use upvote to "mark as read" but reddit annoyingly prevents upvoting after
# 6 months, so this returns false for those, since i can then hide them instead
def can_upvote(post):
	when = datetime.datetime.fromtimestamp(int(post.created_utc))
	max_age = datetime.datetime.now() + relativedelta(months=-6)

	return when > max_age
