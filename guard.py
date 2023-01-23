import datetime
import socket
import pytz as pytz

breaks = ["8 45 8 55", "9 40 9 50", "10 35 10 45", "11 30 11 40", "12 25 12 45", "13 30 13 50", "14 35 14 40", "15 25 15 30", "17 43 17 50"]


def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return startTime <= nowTime <= endTime
    else:
        # over midnight
        return nowTime <= startTime or nowTime >= endTime


def isWorkweekNow():
    return str(datetime.datetime.today().weekday()) in "12345"


def isBreakNow():
    then = datetime.datetime.now(pytz.utc)
    nowTime = then.astimezone(pytz.timezone("Europe/Warsaw")).time()

    for element in breaks:

        a = element.split(" ")
        startTime = datetime.time(int(a[0]), int(a[1]))
        endTime = datetime.time(int(a[2]), int(a[3]))

        if isNowInTimePeriod(startTime, endTime, nowTime):
            return True
    return False


def isInternet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def canPlay():
    return True
    if isBreakNow() and isInternet() and isWorkweekNow():
        return True
    else:
        return False
