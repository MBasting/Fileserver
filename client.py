import time
from ftplib import FTP
from os import walk
from os.path import join, exists
from sys import argv

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


# FTP server using : https://www.techinfected.net/2017/07/create-simple-ftp-server-client-in-python.html
# Observer using: Watchdog
# Requirements:
# - Add folder with content
# - Move folder from outside inside
# - Move folder with content one level up


def client():
    def initial_sync(client_path):
        for root, dirs, files in walk(client_path):
            for dir_ in dirs:
                full_path = join(root, dir_)
                relative_path = full_path[len(client_path) + 1:]
                ftp.mkd(relative_path)

            for filename in files:
                full_path = join(root, filename)
                relative_path = full_path[len(client_path) + 1:]
                ftp.storbinary('STOR ' + relative_path, open(full_path, 'rb'))

    def on_created(event):
        path = event.src_path[len(client_path)+1:]
        if event.is_directory:
            ftp.mkd(path)
        else:
            ftp.storbinary('STOR '+path, open(event.src_path,'rb'))
        print(f"hey, {path} has been created")

    def on_deleted(event):
        path = event.src_path[len(client_path) + 1:]
        if event.is_directory:
            ftp.rmd(path)
        else:
            ftp.delete(path)

    def on_modified(event):
        path = event.src_path[len(client_path)+1:]
        if not event.is_directory:
            ftp.storbinary('STOR ' + path, open(event.src_path, 'rb'))
            print(f"hey, {event.src_path} has been modified")

    def on_moved(event):
        print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")
        src_path = event.src_path[len(client_path) + 1:]
        dst_path = event.dest_path[len(client_path) + 1:]
        try:
            ftp.rename(src_path, dst_path)
        except:
            print("File already moved another time and no longer in this position")
            # Need to check if this is actually the case for file
            if not event.is_directory:
                try:
                    ftp.size(dst_path) # Check if the file is actually moved
                except:
                    raise FileNotFoundError




    print("CLIENT STARTED", argv)
    client_path = argv[-2]
    patterns = ["*"] # Handle all the filetypes
    go_recursively = True
    ignore_patterns = None
    ignore_directories = False
    case_sensitive = True
    ftp = FTP('')
    ftp.connect('localhost', 1026)
    ftp.login('user', '12345') # Specify user and login
    ftp.cwd(".")

    initial_sync(client_path)

    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved

    my_observer = Observer()
    my_observer.schedule(my_event_handler, client_path, recursive=go_recursively)
    my_observer.start()
    print("OBSERVER STARTED")
    try:
        while True:
            time.sleep(1)
    finally: # If process stopes
        my_observer.stop()
        my_observer.join()
        print("Client Done", argv)