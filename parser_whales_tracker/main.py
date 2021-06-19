import requests
import os
import sys
import dotenv

from loguru import logger

dotenv.load_dotenv(".env")

logger.remove()
logger.add(sys.stderr, level="INFO")


class Parser:
    def __init__(self):
        self._session = requests.Session()
        self.hits = 0
        self.uniq = 0
        self.sales = 0
        self.amount = 0
        self.last_hits = 0
        self.last_uniq = 0
        self.last_sales = 0
        self.last_amount = 0
        self.is_auth = False

    def login(self):
        url = f"{URL}/api/auth/login"
        data = {"username": LOGIN, "password": PASSWORD}
        res = self._session.post(url, json=data)
        if not res.status_code == 201:
            raise Exception("Error on auth")
        self.is_auth = True

    def logout(self):
        self._session.get(f"{URL}/api/auth/logout")

    def get_stats(self):
        res = self._session.get(f"{URL}/api/info/stats/dashboard?type=day")
        if not res.status_code == 200:
            raise Exception("Error get_stats")
        js = res.json()

        stats = js.get("stats", {})
        last_click = js.get("last_click", {})
        if not stats or not last_click:
            return
        for hour in stats:
            self.amount += hour.get("amount", 0)
            self.last_amount += hour.get("amount_last", 0)
            self.sales += hour.get("sales", 0)
            self.last_sales += hour.get("sales_last", 0)
            self.hits += hour.get("hits", 0)
            self.last_hits += hour.get("hits_last", 0)
            self.uniq += hour.get("uniques", 0)
            self.last_uniq += hour.get("uniques_last", 0)
        logger.info(
            f"TODAY. Hit: {self.hits} Uniq: {self.uniq} Sale: {self.sales} Amount: {round(self.amount, 2)}"
        )
        logger.info(
            f"Yesterday. Hit: {self.last_hits} Uniq: {self.last_uniq} Sale: {self.last_sales} Amount: {round(self.last_amount, 2)}"
        )

    def get_ua(self):
        pass

    def work(self):
        try:
            self.login()
            self.get_stats()
        except Exception as e:
            logger.error(f"Error: {e}")
            if self.is_auth:
                self.logout()


if __name__ == "__main__":
    pars = Parser()
    LOGIN = os.environ.get("LOGIN")
    PASSWORD = os.environ.get("PASSWORD")
    URL = os.environ.get("URL")

    pars.work()
