import datetime

now = datetime.datetime.now()
__version__ = f"0.1.0a{now.strftime('%Y%m%d%H%M')}"
