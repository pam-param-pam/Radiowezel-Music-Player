class Song:

    def __init__(self, id: str, title: str, author: str, thumbnail: str, length: int):
        self.id = id
        self.title = title
        self.author = author
        self.thumbnail = thumbnail
        self.length = length

    def __str__(self) -> str:
        return self.title

    # def __dict__(self):
        # return {'id': self.id, 'title': self.title, 'author': self.author, 'thumbnail': self.thumbnail, 'length': self.length}

    def __repr__(self):
        return self.title
