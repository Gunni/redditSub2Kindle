# redditSub2Kindle
redditSub2Kindle is a django app that lets you subscribe to stories being posted by redditors.

It has a few assumptions, such as a common title fragment in their stories.

You are able to add multiple subscriptions per username though.

Good example subscription:
- Author: `Ralts_Bloodthorne`
- Subreddit: `HFY`
- Title Fragment: `First Contact`

# Setup
Configure praw, I left an example config and praw_auth.py

# Screenshots

This is what the index page looks like

![the application index page](screenshot-1.png "the application index page")

And here is a single subscription page

![a single subscription page](screenshot-2.png "a single subscription page")

And this is the all subscriptions page

![Image showing the application index page](screenshot-3.png "Image showing the application index page")
