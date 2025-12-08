# OPTIONAL: for long-term storing history
class SpotifyRepository:
    def __init__(self, session):
        self.session = session

    def save_tracks(self, df):
        # insert rows into SQLite
        pass
