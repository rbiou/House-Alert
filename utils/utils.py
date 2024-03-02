from time import time

def log(message: str = "Log", domain: str = "app"):
    print("\033[90m{timestamp}\033[0m｜[House-Alert] [{domain}] {message}".format(
        timestamp = int(time()),
        domain = domain,
        message = message
    ))