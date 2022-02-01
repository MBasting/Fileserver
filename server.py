from sys import argv

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


def server():
    server_path = argv[-1]

    # Instantiate a dummy authorizer for managing 'virtual' users
    authorizer = DummyAuthorizer()

    # Add new user having full r/w permission
    authorizer.add_user('user', '12345', server_path, perm='elradfmwMT')

    # Instantiate FTP handler class
    handler = FTPHandler
    handler.authorizer = authorizer

    # Define a customized banner (string returned when client connects)
    handler.banner = "pyftpdlib based ftpd ready."

    server = FTPServer(("127.0.0.1", 1026), handler)
    try:
        server.serve_forever()
    finally:
        server.close()
        print("Server Done", argv)