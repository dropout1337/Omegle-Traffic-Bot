import os
import sys
import time
import yaml
import ctypes
import requests
import emoji_list
from urllib import parse
from random import choice
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor

if sys.platform == "linux":
    os.system("clear")
else:
    os.system("cls")

class Log:

    def __init__(self):
        self.colours = {
            "reset": "\x1b[0m",
            "success": "\x1b[38;5;10m",
            "info": "\x1b[38;5;45m",
            "warn": "\x1b[38;5;11m",
            "error": "\x1b[38;5;9m"
        }

    def success(self, text: str):
        print("\x1b[0m \x1b[38;5;10mSUCCESS\x1b[0m | \x1b[38;5;10m%s" % (text))

    def info(self, text: str):
        print("\x1b[0m \x1b[38;5;45mINFO\x1b[0m | \x1b[38;5;45m%s" % (text))

    def warn(self, text: str):
        print("\x1b[0m \x1b[38;5;11mWARNING\x1b[0m | \x1b[38;5;11m%s" % (text))

    def error(self, text: str):
        print("\x1b[0m \x1b[38;5;9mERROR\x1b[0m | \x1b[38;5;9m%s" % (text))

class Omegle():

    def __init__(self):
        self.logging = Log()

        self.headers = headers = {
            "authority": "waw1.omegle.com",
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "origin": "https://www.omegle.com",
            "referer": "https://www.omegle.com/",
            "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Brave\";v=\"109\", \"Chromium\";v=\"109\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        }

        with open("config.yml") as f:
            self.config = yaml.safe_load(f.read())

        self.server = self.config["omegle"]["server"]
        self.camera = self.config["omegle"]["video"]
        self.text = self.config["omegle"]["text"]
        
        if self.camera == True and self.text == True:
            self.logging.error("Please only set either video or text to true")
            input()
            sys.exit()

        if self.config["events"]["wait_for_message"] == True and self.config["events"]["wait_for_typing"] == True:
            self.logging.error("Please only set either wait_for_message or wait_for_typing to true")
            input()
            sys.exit()
        
        self.disconnect_after = self.config["omegle"]["disconnect_after"]
        self.proxy_type = self.config["proxy"]["type"]
    
        with open("messages.txt", encoding="utf-8") as f:
            self.messages = [i.strip() for i in f]

        with open("proxies.txt", encoding="utf-8") as f:
            self.proxies = [i.strip() for i in f]

        self.servers = ["front13", "front32", "front12", "front2", "front18", "front29", "front7", "front45", "front44", "front11", "front37", "front46", "front23", "front35", "front19", "front8", "front17", "front47", "front14", "front25", "front22", "front31", "front34", "front48", "front40", "front27", "front33", "front5", "front24", "front10", "front26", "front20", "front42", "front6", "front41", "front39", "front30", "front38", "front36", "front3", "front28", "front4", "front9", "front21", "front15", "front43", "front16"]
        self.an_servers = ["waw1.omegle.com", "waw2.omegle.com", "waw4.omegle.com", "waw3.omegle.com"]

        self.proxy = cycle(self.proxies)
        self.message = cycle(self.messages)

        self.sent = 0
        self.failed = 0

    def title_task(self):
        while True:
            ctypes.windll.kernel32.SetConsoleTitleW("[Omegle Traffic Bot] - Successfully Sent (%s/%s)" % (self.sent, (self.failed + self.sent)))

    def create_session(self):
        proxy = next(self.proxy)

        session = requests.Session()
        session.proxies.update({
            "https": "%s://%s" % (self.proxy_type, proxy)
        })

        session.headers.update(self.headers)

        if self.server == None:
            server = choice(self.servers)
        else:
            server = self.server

        return session, server

    def get_cc(self, session: requests.Session):
        response = session.post("https://%s/check" % (choice(self.an_servers)))
        return response.text

    def create_client(self):
        session, server = self.create_session()
        user_id = os.urandom(8).hex()[:7]
        cc = self.get_cc(session)

        if self.camera:
            url = "https://%s.omegle.com/start?caps=recaptcha2,t3&firstevents=1&spid=&randid=%s&lang=en&camera=OBS Virtual Camera&webrtc=1&cc=%s" % (server, user_id, cc)
        else:
            url = "https://%s.omegle.com/start?caps=recaptcha2,t3&firstevents=1&spid=&randid=%s&cc=%s&lang=en" % (server, user_id, cc)

        if self.config["filters"]["topics"] != []:
            url += "&topics=%s" % (parse.quote_plus(str(self.config["filters"]["topics"]).replace(" ", "")))

        response = session.post(url)

        if "connected" in response.text:
            self.logging.info("Created client %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["info"], response.json()["clientID"], self.logging.colours["reset"]))
            return session, server, response.json()["clientID"]
        else:
            self.logging.error(response.text)
            self.failed += 1
            return False

    def event(self, session: requests.Session, server: str, client_id: str):
        data = {
            "id": client_id
        }
        for x in range(self.config["events"]["timeout"]):
            response = session.post("https://%s.omegle.com/events" % (server), data=data)
            if self.config["events"]["wait_for_message"]:
                if "gotMessage" in response.text:
                    self.logging.info("Received message event %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["info"], response.json()[0][1], self.logging.colours["reset"]))
                    return
            if self.config["events"]["wait_for_typing"]:
                if "typing" in response.text:
                    self.logging.info("Received typing event %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["info"], "typing", self.logging.colours["reset"]))
                    return

            time.sleep(1)

    def disconnect(self, session: requests.Session, server: str, client_id: str):
        data = {
            "id": client_id
        }
        response = session.post("https://%s.omegle.com/disconnect" % (server), data=data)
        if "win" in response.text:
            self.logging.success("Disconnected %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["success"], client_id, self.logging.colours["reset"]))
        else:
            pass#self.logging.error("Failed to disconnect %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["error"], client_id, self.logging.colours["reset"]))

    def typing(self, session: requests.Session, server: str, client_id: str):
        data = {
            "id": client_id
        }
        response = session.post("https://%s.omegle.com/typing" % (server), data=data)
        if "win" in response.text:
            self.logging.info("Started typing %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["info"], client_id, self.logging.colours["reset"]))
        else:
            pass#self.logging.error("Failed to start typing %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["error"], client_id, self.logging.colours["reset"]))

    def send(self, session: requests.Session, server: str, client_id: str):
        message = next(self.message)
        message.replace("<newline>", "%0") 
        
        data = {
            "id": client_id,
            "msg": message
        }

        if self.config["message"]["prefix"] != "":
            data["msg"] = "%s %s" % (self.config["message"]["prefix"], message)

        if self.config["message"]["emoji"]:
            data["msg"] += " %s" % (choice(emoji_list.all_emoji))

        if self.config["message"]["string"]:
            data["msg"] += " %s" % (os.urandom(5).hex()[:5])
        
        if self.config["message"]["suffix"] != "":
            data["msg"] += " %s" % (self.config["message"]["suffix"])
        
        response = session.post("https://%s.omegle.com/send" % (server), data=data)
        if "win" in response.text:
            self.logging.info("Sent message %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["info"], data["msg"], self.logging.colours["reset"]))
            self.sent += 1
        else:
            pass#self.logging.error("Failed to send message %s(%s%s%s)" % (self.logging.colours["reset"], self.logging.colours["error"], client_id, self.logging.colours["reset"]))

    def task(self):
        try:
            session, server, client_id = self.create_client()
            
            if session == False:
                return

            if self.config["events"]["wait_for_message"] == True or self.config["events"]["wait_for_typing"] == True:
                self.event(session, server, client_id)

            if self.config["omegle"]["trigger_typing"]:
                self.typing(session, server, client_id)
                
            self.send(session, server, client_id)
            time.sleep(self.disconnect_after)
            self.disconnect(session, server, client_id)
        except Exception as e:
            #self.logging.error(e)
            self.failed += 1

    def run(self):
        with ThreadPoolExecutor(max_workers=1000) as self.executor:
            self.executor.submit(self.title_task)
            while True:
                self.executor.submit(self.task)
            
if __name__ == "__main__":
    client = Omegle()
    client.run()
