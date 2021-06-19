import requests
import os
import sys
import dotenv
import schedule
import time
from datetime import datetime
from pytz import timezone


from loguru import logger

dotenv.load_dotenv(".env")

logger.remove()
logger.add(sys.stderr, level="INFO")

LOGIN = os.environ.get("LOGIN")
PASSWORD = os.environ.get("PASSWORD")
URL = os.environ.get("URL")
TELEGRAM_TOKEN = os.environ.get("TOKEN")
TELEGRAM_ID = os.environ.get("ID")
TZ = os.environ.get("TZ")


class Parser:
    def __init__(self):
        self._session = requests.Session()
        self.is_auth = False
        self.prev_uniq = 0
        self.prev_hits = 0
        self.prev_sales = 0
        self.prev_amount = 0

    def send_telegram(self, msg):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_ID}&text={msg}"
            with requests.Session() as s:
                s.get(url)
        except Exception as e:
            logger.error(f"Error on send telegram: {e}")

    @property
    def get_time(self):
        dt_format = "%d/%m/%Y %H%M"
        zone = datetime.now(timezone(TZ))
        return zone.strftime(dt_format)

    def setlstinfile(self, filename, lst):
        try:
            old_count = 0
            with open(filename, "r", encoding="utf-8") as f:
                old_list = f.read().split("\n")
                lst = list(set(old_list + lst))
                old_count = len(old_list)
        except FileNotFoundError:
            logger.error(f"Create new file: {filename}")
        logger.info(f"File {filename} string {old_count}. New string {len(lst)}")
        with open(filename, "w", encoding="utf-8") as f:
            for item in list(set(lst)):
                f.write("%s\n" % item)

    def login(self):
        if self.is_auth:
            logger.info(f"Already auth {self._session.cookies}")
            return
        url = f"{URL}/api/auth/login"
        data = {"username": LOGIN, "password": PASSWORD}
        res = self._session.post(url, json=data)
        if not res.status_code == 201:
            raise Exception("Error on auth")
        self.is_auth = True

    def logout(self):
        self.is_auth = False
        self._session.get(f"{URL}/api/auth/logout")
        self._session.cookies.clear()

    def get_stats(self):
        hits = 0
        uniq = 0
        sales = 0
        amount = 0
        last_hits = 0
        last_uniq = 0
        last_sales = 0
        last_amount = 0
        res = self._session.get(f"{URL}/api/info/stats/dashboard?type=day")
        if not res.status_code == 200:
            raise Exception("Error get_stats")
        js = res.json()

        stats = js.get("stats", {})
        last_click = js.get("last_click", {})
        if not stats or not last_click:
            return
        for hour in stats:
            amount += hour.get("amount", 0)
            last_amount += hour.get("amount_last", 0)
            sales += hour.get("sales", 0)
            last_sales += hour.get("sales_last", 0)
            hits += hour.get("hits", 0)
            last_hits += hour.get("hits_last", 0)
            uniq += hour.get("uniques", 0)
            last_uniq += hour.get("uniques_last", 0)
        msg_today = f"STATS: {hits}|{uniq}|{sales}|{round(amount, 2)}"
        logger.info(f"TODAY. {msg_today}")
        logger.info(
            f"Yesterday. {last_hits}|{last_uniq}|{last_sales}|{round(last_amount, 2)}"
        )

        lst_ua = [click["useragent"] for click in last_click]
        if lst_ua:
            self.setlstinfile("temp/ua.txt", lst_ua)

        if self.prev_hits >= hits:
            return

        self.send_telegram(f"{self.get_time} {msg_today}")
        if self.prev_hits:
            msg = f"Add {hits-self.prev_hits}|{uniq-self.prev_uniq}|{sales-self.prev_sales}|{round(amount-self.prev_amount, 2)}"
            self.send_telegram(msg)
            logger.info(msg)
        self.prev_sales = sales
        self.prev_hits = hits
        self.prev_uniq = uniq
        self.prev_amount = amount

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
    pars.work()

    schedule.every().hour.at(":28").do(pars.work)
    schedule.every().hour.at(":58").do(pars.work)

    while True:
        schedule.run_pending()
        time.sleep(1)
