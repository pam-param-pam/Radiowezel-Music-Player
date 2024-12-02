import datetime
import socket
import pytz as pytz

breaks = ["8 46 8 56", "9 41 9 51", "10 36 10 46", "11 31 11 41", "12 26 12 46", "13 31 13 51", "14 36 14 41", "15 26 15 31"]


def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return startTime <= nowTime <= endTime
    else:
        # over midnight
        return nowTime <= startTime or nowTime >= endTime


def isWorkweekNow():
    #print(str(datetime.datetime.today().weekday()))
    return str(datetime.datetime.today().weekday()) in "01234"


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
    #print("isBreakNow: " + str(isBreakNow()))
    #print("isInternet: " + str(isInternet()))
    #print("isWorkweekNow(): " + str(isWorkweekNow()))
    return True
    return bool(isBreakNow() and isInternet() and isWorkweekNow())

