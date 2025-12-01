import time

__version__ = "1.1.0"
StartTime = time.time()

class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"
