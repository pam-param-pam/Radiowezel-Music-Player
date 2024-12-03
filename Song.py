class Song:

    def __init__(self, id: str, title: str, author: str, thumbnail: str, length: int):
        self.id = id
        self.title = title
        self.author = author
        self.thumbnail = thumbnail
        self.length = length
        self.url = None

    def __str__(self) -> str:
        return self.title

    def __repr__(self):
        return self.title
