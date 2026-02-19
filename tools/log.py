def info(message):
    print(f"\033[94m[INFO]\033[0m {message}")

def error(message):
    print(f"\033[91m[ERROR]\033[0m {message}")

def warning(message):
    print(f"\033[93m[WARNING]\033[0m {message}")

def fatal_error(message):
    error(message)
    exit(1)

def success(message):
    print(f"\033[92m[SUCCESS]\033[0m {message}")

def progress(message, done=False):
    if done:
        print(f"\033[96m[DONE]\033[0m {message}")
    else:
        print(f"\033[96m[PROGRESS]\033[0m {message}", end='\r')
