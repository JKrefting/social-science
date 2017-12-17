""" Keeps track of new posts and stores them as html files. """

import io
import locale
import os
import re
import argparse
import sqlite3
import logging
from datetime import datetime
from datetime import timedelta
from apscheduler.schedulers.blocking import BlockingScheduler

import requests
from bs4 import BeautifulSoup

from dpat_config import *

def commandline():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--interval",
        type=int,
        required=False,
        default=60,
        help="Time interval for checks (in minutes)."
    )
    return parser.parse_args()

def getContent(session, url):
# get html code from url and return as soup object
    try:
        response = session.get(url, timeout=5, stream=False)
    except requests.exceptions.RequestException as e:
        logging.error(str(e))

    # check for other (noncritical) errors
    if not response.status_code == requests.codes.ok:
        logging.warning(response.raise_for_status())

    # parse code to soup
    soup = BeautifulSoup(response.text, 'html.parser')
    return(soup)

def adjustThreads(db_cursor, thread_user_name, thread_time,
                  thread_title, thread_url, BASE_URL):
# adjust with db: enter new thread into Threads table,
# returns a dict with thread id and a flag indicating if it was newly created
    is_new_thread = False
    # check if thread exists
    db_cursor.execute("SELECT ThreadID FROM Threads"
                      " WHERE UserName = ? AND Time = ?", (thread_user_name, thread_time,))
    thread_id = db_cursor.fetchone()
    # if thread does not exist, create entry
    if thread_id is None:
        is_new_thread = True
        # logging.info("New thread opened by user {} at {}.".format(thread_user_name, thread_time))
        # enter new thread into db
        db_cursor.execute("INSERT INTO Threads(UserName, Time, Title, ThreadURL, BaseURL)"
                          " VALUES(?, ?, ?, ?, ?)", (thread_user_name, thread_time, thread_title, thread_url, BASE_URL, ))
        # get new thread id
        thread_id = db_cursor.lastrowid
    # return id of new or already existing thread
    dict = {
        'id': thread_id,
        'is new': is_new_thread,
        'url': thread_url
    }
    return(dict)

def adjustPosts(db_cursor, thread_id, post_user_name,
                post_time, post_url, BASE_URL):
# adjust with db: enter new post into Posts table,
# returns a dict with post id and a flag indicating if it was newly created
    is_new_post = False
    db_cursor.execute("SELECT PostID FROM Posts"
                      " WHERE UserName = ? AND Time = ?", (post_user_name, post_time,))
    post_id = db_cursor.fetchone()
    # if post does not exist, create entry
    if post_id is None:
        is_new_post = True
        # enter new post into db
        db_cursor.execute("INSERT INTO Posts(ThreadID, UserName, Time, PostURL, BaseURL)"
                          " VALUES(?, ?, ?, ?, ?)", (thread_id, post_user_name, post_time, post_url, BASE_URL, ))
        post_id = db_cursor.lastrowid
    # return id of new or already existing post
    dict = {
        'id': post_id,
        'is new': is_new_post,
        'url': post_url
    }
    return(dict)

def main():

    logging.info("Starting check.")

    # ------------------------------------------------------------------------------------------------------------------
    # log into page for session

    # open session to persist parameters and cookies
    session = requests.Session()

    # hide bot identity for session
    user_agent = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}
    session.headers.update(user_agent)

    # log into page
    login_payload = {
        'loginUsername': LOGIN_NAME,
        'loginPassword': LOGIN_PW
    }
    try:
        response = session.post(BASE_URL + LOGIN_URL, timeout=5, stream=False, data=login_payload)
        # check if login successful
        if response.status_code == requests.codes.ok:
            logging.info("Login successful.")
        else:
            logging.error("Login failed.")
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(str(e))

    # ------------------------------------------------------------------------------------------------------------------
    # find new posts on LATEST_POSTS_URL

    # read page indicating the latest posts
    html_soup = getContent(session, BASE_URL + LATEST_POSTS_URL)

    # parse thread table
    thread_table = html_soup.find('table')
    thread_rows = thread_table.find_all('tr')
    thread_rows.pop(0)  # lose table header

    # connect to db
    db_con = sqlite3.connect('forum.db')
    with db_con:
        # cursor to work on the db
        db_cursor = db_con.cursor()

        # --------------------------------------------------------------------------------------------------------------
        # extract post and thread meta info

        for row in thread_rows:
            # thread meta info
            anchors = row.find_all('a')
            thread_title = anchors[0].get_text()
            thread_url = anchors[0].get('href')
            thread_user_name = anchors[1].get_text()
            raw_time = row.find_all('p')[1].get_text()
            raw_time = raw_time[raw_time.find("(") + 1:raw_time.find(")")]
            thread_time_dt = datetime.strptime(raw_time, '%d. %B %Y, %H:%M')
            thread_time = thread_time_dt.__str__()

            # post meta info
            try:
                post_user_name = anchors[4].get_text()
            except IndexError:
                post_user_name = thread_user_name
            try:
                post_url = anchors[3].get('href')
            except IndexError:
                post_url = thread_url
            try:
                raw_time = row.find_all('p')[4].get_text()
                raw_time = raw_time[raw_time.find("(") + 1:raw_time.find(")")]
                post_time_dt = datetime.strptime(raw_time, '%d. %B %Y, %H:%M')
                post_time = post_time_dt.__str__()
                post_date = post_time_dt.date().__str__()
            except IndexError:
                post_time_dt = thread_time_dt
                post_time = post_time_dt.__str__()
                post_date = post_time_dt.date().__str__()

            # ----------------------------------------------------------------------------------------------------------
            # adjust meta info with db, save new post as html

            # adjust with Threads in db
            thread_info = adjustThreads(db_cursor, thread_user_name, thread_time,
                                        thread_title, thread_url, BASE_URL)

            # adjust with Posts in db, get id if post is new
            post_info = adjustPosts(db_cursor, thread_info['id'], post_user_name,
                                    post_time, post_url, BASE_URL)

            # save html of new post
            if post_info['is new']:
                # create directory to store htmls
                dir_path = os.path.join(SAVE_PATH, post_date)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                # get post
                # db_cursor.execute("SELECT PostURL FROM Posts WHERE PostID = ?", (post_id, ))
                # post_url = db_cursor.fetchone()
                html_soup = getContent(session, BASE_URL + post_info['url'])

                # save html
                file_name = post_time.replace(":", "-") + " " + post_user_name + '.html'
                file_path = os.path.join(dir_path, file_name)
                with io.open(file_path, 'w', encoding='utf8') as file:
                    file.write(str(html_soup))

                logging.info("Saved new post of user {} at {}, saved as html.".format(post_user_name, post_time))
    logging.info("Check ended.")

if __name__ == "__main__":

    # start log
    logging.basicConfig(
        filename='dpat_snap.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s (%(name)s)'
    )
    logging.getLogger().addHandler(logging.StreamHandler())     # show messages also in console

    # get commandline arguments
    args = commandline()

    # set locale for datetime conversion
    locale.setlocale(locale.LC_ALL, 'deu_deu')

    # schedule call of main function
    scheduler = BlockingScheduler()
    scheduler.add_job(
        main,
        'interval',
        minutes=args.interval,
        start_date=datetime.now() + timedelta(seconds=1)
    )
    logging.info('Scheduler configured with {} minute interval. Press Ctrl + Break to exit.'.format(args.interval))

    try:
        scheduler.start()
    except KeyboardInterrupt:
        sys.exit()

# code to execute for debugging in console
# table = db.execute("SELECT * FROM Threads ORDER BY Time DESC")
# for t in table: print(t)
# request.head
# request.response.head
# request.cookies

