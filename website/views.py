import praw
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from prawcore import BadJSON

from .models import Author, Story
from .utils import get_reddit_posts, can_upvote, wipe_cache, downloadPostWithComments, sort_posts


@require_http_methods(["GET"])
def index(request):
	authors = Author.objects.filter(enabled=True)
	stories = Story.objects.filter(enabled=True)

	author_stories = []

	for author in authors:
		obj_stories = []

		for story in stories:
			if story.author == author:
				obj_stories.append(story)

		author_stories.append({'author': author, 'stories': obj_stories})

	context = {'payload': author_stories}

	return render(request, 'index.html', context)

@require_http_methods(["GET"])
def all(request):
	authors = Author.objects.filter(enabled=True)

	posts = []

	for author in authors:
		sub_posts = []

		try:
			sub_posts = get_reddit_posts(author, None, 0)
		except BadJSON as e:
			print(f'{author} returned {e}')
			continue

		posts.extend(sub_posts)

	return render(request, 'detail.html', { 'posts': sort_posts(posts) })

@require_http_methods(["GET"])
def detail(request, story_id):
	story = get_object_or_404(Story, pk=story_id)
	author = get_object_or_404(Author, pk=story.author.id)

	return render(request, 'detail.html', {
		'story': story,
		'author': author,
		'posts': get_reddit_posts(author, story)
	})

@require_http_methods(["GET", "POST"])
def vote(request, vote_id):
	reddit = praw.Reddit()
	post = reddit.submission(vote_id)

	if can_upvote(post):
		upvote_state = post.likes

		if upvote_state is None:
			post.upvote()
		elif upvote_state: # is True
			post.clear_vote()
		else:
			raise NotImplemented()
	else:
		if post.hidden:
			post.unhide()
		else:
			post.hide()

	wipe_cache(post.id)

	# Return fake file download with bullshit content type so that we don't redirect the user
	# Very helpful for kindle users to be able to download many posts and upvote them too
	response = HttpResponse('', content_type='application/vnd+reddit.sub')
	response['Content-Description'] = 'File Transfer'
	response['Content-Disposition'] = f'attachment; filename="success"'

	return response

@require_http_methods(["GET"])
def download(request, post_id):
	return downloadPostWithComments(post_id)

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
		return downloadPostWithComments(post.id)

	raise NotImplementedError()
