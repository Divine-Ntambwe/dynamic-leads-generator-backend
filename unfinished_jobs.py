from dotenv import load_dotenv
from database import Database

load_dotenv()

class UnfinishedJobs:
    def __init__(self):
        self.db = Database()
        pass

    async def run():
        pass
