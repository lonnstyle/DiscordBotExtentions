import json
from log import logger
import os

import requests

logger = logger.getLogger('language')
class language():
    def init(self):
        try:
            self.zh_hant = json.loads(requests.get("https://raw.githubusercontent.com/lonnstyle/DiscordBotExt-loc/master/locales/zh-hant.json").text)
            self.zh_hans = json.loads(requests.get("https://raw.githubusercontent.com/lonnstyle/DiscordBotExt-loc/master/locales/zh-hans.json").text)
            self.en = json.loads(requests.get("https://raw.githubusercontent.com/lonnstyle/DiscordBotExt-loc/master/locales/en.json").text)
            logger.debug("[init] successfully pulled loc file from github")
        except Exception as exc:
            logger.error(exc)
        self.pref = json.load(open("setting.json", 'r', encoding='utf8'))
        self.pref = self.pref.get("language", "zh-hant")
        logger.debug(f'[init] language preference set: {self.pref}')

    def langpref(self, lang=None):
        if lang and lang in ["zh-hant", "zh-hans", "en"]:
            lang = lang.replace("-", "_")
            return getattr(self, lang)
        if self.pref == 'zh-hant':
            return self.zh_hant
        elif self.pref == 'zh-hans':
            return self.zh_hans
        elif self.pref == 'en':
            return self.en
        else:
            try:
                return json.load(open(self.pref, "r", encoding='utf8'))
            except Exception as exc:
                logging.critical(exc)


# lang = language()
