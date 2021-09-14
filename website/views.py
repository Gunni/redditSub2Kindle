import time
from collections import defaultdict

import praw
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from prawcore import BadJSON
from django.db.models import Subquery

from .model_author import Author, AuthorForm
from .model_story import Story
from .utils import get_reddit_posts, can_upvote, wipe_cache, sort_posts, \
	download_ebook_with_comments


@require_http_methods(["GET"])
def index(request):
	stories = Story.objects.filter(enabled=True).select_related('author').filter(enabled=True)

	res = defaultdict(list)
	author_stories = []

	for story in stories:
		res[story.author].append(story)

	for author, stories in res.items():
		author_stories.append({'author': author, 'stories': stories})

	context = {'payload': author_stories}

	return render(request, 'index.html', context)

@require_http_methods(["GET"])
def all(request):
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

@require_http_methods(["GET"])
def detail(request, story_id):
	story = get_object_or_404(Story, pk=story_id)
	author = get_object_or_404(Author, pk=story.author.id)

	return render(request, 'detail.html', {
		'story': story,
		'author': author,
		'posts': get_reddit_posts(author, story, int(request.GET.get('n', 3)))
	})

@require_http_methods(["GET", "POST"])
def vote(request, vote_id):
	reddit = praw.Reddit()
	post = reddit.submission(vote_id)
	wipe_cache(post.id)

	if can_upvote(post):
		upvote_state = post.likes

		if upvote_state is None:
			post.upvote()
			action = 'upvoted'
		elif upvote_state: # is True
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

@require_http_methods(["GET"])
def download_ebook(request, post_id):
	return download_ebook_with_comments(post_id)

@require_http_methods(["POST"])
def direct(request):
	p = request.POST

	if not ('download' in p):
		raise NotImplementedError()

	if not 'url' in p:
		raise NotImplementedError()

	reddit = praw.Reddit()

	# If url is not a reddit host, this will return a InvalidURL exception
	post = reddit.submission(url=p['url'])

	if 'download' in p:
		return download_ebook_with_comments(post.id)

	raise NotImplementedError()

@require_http_methods(["GET"])
def authors(request):
	authors = Author.ordered_objects.all()
	return render(request, 'authors.html', { 'authors': authors })

@require_http_methods(["GET", "POST"])
def author(request, author_id):
	if request.method == 'POST':
		form = AuthorForm(request.POST)

		if form.is_valid():
			form.save()
			return redirect('authors')
		else:
			raise NotImplementedError()

	if author_id == 0:
		return render(request, 'author.html', { 'form': AuthorForm() })

	author = get_object_or_404(Author, pk=author_id)
	return render(request, 'author.html', { 'form': AuthorForm(instance=author) })

@require_http_methods(["POST", "OPTIONS"])
def get_all(request, story_id):
	if request.method == 'OPTIONS':
		r = HttpResponse('')
		r['Access-Control-Allow-Origin'] = 'http://10.0.10.10:8000/'
		r['Access-Control-Allow-Headers'] = '*'
		r['Access-Control-Allow-Methods'] = 'GET,OPTIONS'
		return r

	story = get_object_or_404(Story, pk=story_id)
	author = get_object_or_404(Author, pk=story.author.id)

	posts = get_reddit_posts(author, story)

	ret = {
		'posts': []
	}

	for post in posts:
		if post.likes == True or post.hidden == True:
			print(f'Skipping {post.title}')
			continue

		ret['posts'].append(f'/download_ebook/{post.id}/')

		# I could auto upvote the posts here, but that would be against the rules
		# https://www.reddit.com/r/redditdev/comments/mpavxn/get_all_and_upvote/

	return JsonResponse(ret)
