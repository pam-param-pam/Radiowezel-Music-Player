class AgeRestrictedVideo(Exception):
    """Age restricted videos are not allowed"""
    pass


class VideoTooLong(Exception):
    """Video is too long"""
    pass


class VideoNotAvailable(Exception):
    """Video is not available"""
    pass


