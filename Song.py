class Song:

    def __init__(self, id, title, author, thumbnail, length):
        self.id = id
        self.title = title
        self.author = author
        self.thumbnail = thumbnail
        self.length = length

    def __str__(self) -> str:
        return self.title

    def __repr__(self):
        return self.title
