import time
from collections import defaultdict

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from prawcore import BadJSON

from . import utils
from .helpers import get_ebook_name_from_list_of_posts
from .model_author import Author
from .utils import *


# Get list of authors+stories
@require_http_methods(["GET"])
def get_list_of_subscriptions(request):
	stories = Story.objects.filter(enabled=True).select_related('author').filter(enabled=True)

	res = defaultdict(list)
	author_stories = []

	for story in stories:
		res[story.author].append(story)

	for author, stories in res.items():
		author_stories.append({'author': author, 'stories': stories})

	context = {'payload': author_stories}

	return render(request, 'index.html', context)


# Gets unread posts for ALL stories
@require_http_methods(["GET"])
def get_all_posts_of_all_subscriptions(request):
	authors = Author.ordered_objects.filter(enabled=True)

	posts = []

	start = time.time()

	for author in authors:
		try:
			sub_posts = get_reddit_posts(author, None, 0)
		except BadJSON as e:
			print(f'{author} returned {e}')
			continue

		posts.extend(sub_posts)

	print(f'Load time for /all: {time.time() - start:.2f}')

	return render(request, 'detail.html', { 'posts': sort_posts(posts) })


# Takes a story id and returns posts for it
@require_http_methods(["GET"])
def get_list_of_subscription_posts(request, story_id):
	story = get_object_or_404(Story, pk=story_id)
	author = get_object_or_404(Author, pk=story.author.id)

	return render(request, 'detail.html', {
		'story': story,
		'author': author,
		'posts': get_reddit_posts(author, story, int(request.GET.get('n', 3)))
	})


# Implements reddit style voting, returns a fake file with a name saying what action was taken
@require_http_methods(["GET", "POST"])
def vote(_, vote_id):
	reddit = praw.Reddit()
	post = reddit.submission(vote_id)

	wipe_cache(post.id)

	if can_upvote(post):
		upvote_state = post.likes

		if upvote_state is None:
			post.upvote()
			action = 'upvoted'
		elif upvote_state:  # is True
			post.clear_vote()
			action = 'downvoted'
		else:
			raise NotImplemented()
	else:
		if post.hidden:
			post.unhide()
			action = 'unhidden'
		else:
			post.hide()
			action = 'hidden'

	# Return fake file download with so that we don't redirect the user
	# Slightly annoying for desktop users, but suuuper handy for Kindle users
	# Consider only doing this for kindle User Agents?
	response = HttpResponse('', content_type='application/octet-stream')
	response['Content-Description'] = 'File Transfer'
	response['Content-Disposition'] = f'attachment; filename="Post {action}.txt"'

	return response


# Takes in a reddit post id and returns an ebook for it
@require_http_methods(["GET"])
def download_ebook(_, post_id):
	reddit = praw.Reddit()
	post = [ reddit.submission(post_id) ]

	title = get_ebook_name_from_list_of_posts(post)

	return get_posts_as_ebook(post, title, post[0].author)


# Takes in a title and a plaintext body and makes it into an ebook
@require_http_methods(["POST"])
def textbook(request):
	p = request.POST

	if 'title' not in p:
		raise NotImplementedError('title missing')

	if 'content' not in p:
		raise NotImplementedError('content missing')

	return generate_ebook_from_plaintext(p['title'], p['content'])


# Takes in a POST with a textfield that can contain multiple reddit links and returns
# an ebook containing the listed posts
@require_http_methods(["POST"])
def bookify(request):
	p = request.POST

	if 'list' not in p:
		raise NotImplementedError()

	posts = []
	reddit = praw.Reddit()

	# Lines in form post data is split with \r for some reason, not \n or \r\n, odd
	for line in p['list'].split('\r'):
		s = reddit.submission(url=line.strip())
		posts.append(s)

	if len(posts) == 0:
		raise NotImplementedError('cannot handle empty book')

	title = get_ebook_name_from_list_of_posts(posts)

	return get_posts_as_ebook(posts, title, posts[0].author)


@require_http_methods(["GET"])
def get_all_authors(request):
	authors = Author.ordered_objects.all()
	return render(request, 'authors.html', { 'authors': authors })


# @require_http_methods(["GET", "POST"])
# def author(request, author_id):
# 	if request.method == 'POST':
# 		form = AuthorForm(request.POST)
#
# 		if form.is_valid():
# 			form.save()
# 			return redirect('authors')
# 		else:
# 			raise NotImplementedError()
#
# 	if author_id == 0:
# 		return render(request, 'author.html', { 'form': AuthorForm() })
#
# 	author = get_object_or_404(Author, pk=author_id)
# 	return render(request, 'author.html', { 'form': AuthorForm(instance=author) })


# Takes in a story id and if there are unread posts, it returns up to 10 of them
# If there are no unread posts for the story, then it makes a book with all the posts
@require_http_methods(["POST"])
def get_n_chapter_as_ebook(_, story_id):
	story = get_object_or_404(Story, pk=story_id)
	author = get_object_or_404(Author, pk=story.author.id)

	posts = get_reddit_posts(author, story, 0)

	# We only want the oldest, unread, 10 posts.
	posts = posts[-10:]

	# Surprising behavior? If everything is already upvoted, get all posts instead?
	if len(posts) == 0:
		print('# GOING TO GET ALL POSTS BECAUSE posts was empty')
		posts = get_reddit_posts(story.author, story, 10000)

	title = get_ebook_name_from_list_of_posts(posts)

	return get_posts_as_ebook(reversed(posts), title, author)

@require_http_methods(["POST"])
def nuke_cache(_, story_id=None):
	if story_id is None:
		print(f'Nuking THE WHOLE cache for ALL stories')
		cache.clear()
		return redirect('index')

	story = get_object_or_404(Story, pk=story_id)
	posts = get_reddit_posts(story.author, story, 10000)

	for post in posts:
		print(f'Nuking cache for {post.title}')
		utils.wipe_cache(post)

	return redirect('detail', story_id=story_id)
