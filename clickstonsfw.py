import re
import sys
from collections import defaultdict, deque

import praw
from prawcore.exceptions import Forbidden, NotFound, Redirect

reddit = praw.Reddit(client_id='kRt0ra53_uQRRg',
                     client_secret='MPiFjK7TzT6vTYiqUjnmlB6XNEI',
                     user_agent='praw')


def clicks_to_nsfw(startsub: str, returnall: bool = False):
    """Finds a path in the sidebar from one subreddit to an nsfw subreddit if it exists

    Params
    ------
    startsub:
        Name of the starting subreddit
    returnall:
        If True, returns the path, cache, tierlist, and tree as a tuple.
        If False, returns the path
        Default False
    
    Returns
    -------
    path: deque
        The subreddit path
    cache: set
        All of the subreddits parsed
    tierlist: collections.defaultdict
        All of the subreddits parsed, separated by distance from startsub
    tree: collections.defaultdict
        All of the subreddits as a dictionary of connections to other subreddits
    """
    cache = {startsub.lower()}
    startsub = reddit.subreddit(startsub)
    tier = 0
    tierlist = defaultdict(set)
    tierlist[0].add(startsub)
    tree = defaultdict(set)

    def read_sidebar(subreddit):
        """Returns all subreddits in the sidebar

        Params
        ------
        subreddit: praw Subreddit

        Yields
        ------
        praw Subreddit
        """
        sidebar = subreddit.description_html
        if sidebar is None:
            return None
        hrefs = re.finditer(r'href="(?:[^"]*?reddit\.com)?/?r/(\w+)">(?!</a>)', sidebar)
        for i in hrefs:
            try:
                i = i[1].lower()
                if i not in cache:
                    sub = reddit.subreddit(i)
                    #check if sub exists, will raise error if not
                    sub.fullname
                    cache.add(i)
                    yield sub
            except (Forbidden, NotFound, Redirect, TypeError):
                cache.add(i)
    
    def scrape(subs: set):
        """Builds cache, tierlist, and tree. Returns sub name if an nsfw sub is found, else returns None"""
        nonlocal tier, tierlist, tree
        tier += 1
        for sub in subs:
            children = read_sidebar(sub)
            for child in children:
                print(f'\r{sub.display_name.ljust(21)}: {child.display_name.ljust(21)}', end='', flush=True)
                tierlist[tier].add(child)
                tree[sub].add(child)
                if child.over18:
                    return child
        return None
    
    def pathing(subreddit) -> deque:
        """Builds the path from startsub to the param subreddit"""
        nonlocal startsub, tier, tierlist, tree
        queue = deque([subreddit.display_name])
        while tier:
            for sub in tierlist[tier]:
                if subreddit in tree[sub]:
                    queue.appendleft(sub.display_name)
                    subreddit = sub
            tier -= 1
        queue.appendleft(startsub.display_name)
        return queue

    print(f'{"Parent".ljust(21)}: Child')
    while tierlist[tier]:
        branch = scrape(tierlist[tier])
        if branch is not None:
            print('\nPathed!')
            path = pathing(branch)
            if returnall:
                return path, cache, tierlist, tree
            return path
    print('\nFailed to path')
    if returnall:
        return deque(), cache, tierlist, tree
    return deque()


if __name__ == "__main__":
    STARTINGSUB = sys.argv[1]
    if STARTINGSUB.lower() == 'random':
        STARTINGSUB = reddit.random_subreddit().display_name
        print(STARTINGSUB)
    PATH = clicks_to_nsfw(STARTINGSUB)
    if PATH:
        print(' -> '.join(PATH))
