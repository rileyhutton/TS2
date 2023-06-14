##################################################
## TELEGRAM SERVER STATUS (TS2) BY RILEY HUTTON ##
##               RILEYHUTTON.COM                ##
##################################################

from datetime import datetime
import csv
import ping3             ##external dependancy 
import time
import threading
import requests          ##external dependancy

ping_timeout = 4           ## TIME FOR PING TO TIMEOUT - IN SECONDS
ping_frequency = 60        ## SECONDS BETWEEN PINGING DEVICES
alert_after = 1            ## NUMBER OF FAILED PINGS BEFORE USERS ARE ALERTED
statuses = ["Online", "Not Found", "No Reply", "[Not Yet Tested]"]
statusEmojis = ["✅", "👀", "❌", "⏳"]

lastCheck = "Never"

def getDateTime():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class client():
    def __init__(self, ipAddress, name):
        self.ip = ipAddress.strip()
        self.name = name.strip()
        self.lastStatusCode = 3
        self.lastLive = 'N/A'
        self.failCount = 0
        self.usersNotified = True

    def ping(self):
        p = ping3.ping(self.ip, timeout=ping_timeout)
        if p == False:
            ## HOST UNKNOWN
            self.lastStatusCode = 1
            self.failCount += 1
            self.announceFailure()
            return self.lastStatusCode
        elif p == None:
            ## TIMEOUT
            self.lastStatusCode = 2
            self.failCount += 1
            self.announceFailure()
            return self.lastStatusCode
        else:
            ## ONLINE
            self.announceOnline()
            self.lastStatusCode = 0
            self.lastLive = getDateTime()
            self.failCount = 0
            self.usersNotified = False
            return self.lastStatusCode

    def getStatusString(self):
        return statuses[self.lastStatusCode];

    def announceFailure(self):
        if self.usersNotified == True:
            return False
        if self.failCount < alert_after:
            return False
        message = f"⚠️ DEVICE OFFLINE ⚠️\n{self.name} at {self.ip} is currently offline ({self.getStatusString()}). Last live at {self.lastLive}"
        broadcastThread = threading.Thread(target=BroadcastTelegramMessage, args=(message,))   ##REMOVE THIS IF HAVING MULTIPLE THREADS SAME NAME BECOMES ISSUE
        broadcastThread.start()
        self.usersNotified = True
        return True

    def announceOnline(self):
        if self.lastStatusCode in [1,2]:
            message = f"✅ - {self.name} at {self.ip} is back online."
            broadcastThread = threading.Thread(target=BroadcastTelegramMessage, args=(message,))   ##REMOVE THIS IF HAVING MULTIPLE THREADS SAME NAME BECOMES ISSUE
            broadcastThread.start()
            return True
        else:
            return False
        
    def getStatusRow(self):
        output = f"{statusEmojis[self.lastStatusCode]} {self.name} - {self.getStatusString()}"
        if self.lastStatusCode in [1,2]:
            output = output + f" - Last online {self.lastLive}. {self.failCount} failed pings."
        return output

class TelegramUser():
    def __init__(self, apiKey, userID):
        self.user = userID
        self.key = apiKey

    def sendMessage(self, content):
        url = f"https://api.telegram.org/bot{self.key}/sendMessage"
        params = {
            "chat_id": self.user,
            "text": content
        }
        response = requests.post(url, json=params)
        if response.status_code == 200:
            return True
        else:
            print(getDateTime(), "Error sending message to", self.user, "They need to message the bot first.")

def ClientHeartbeat(clients, delay):
    global lastCheck
    while True:
        for c in clients:
            c.ping()
        lastCheck = getDateTime()
        time.sleep(delay)

def ReadCSV(filename):
    with open(filename, newline='') as csvfile:
        return list(csv.reader(csvfile, delimiter=',', quotechar='|'))
    
def ReadTXT(filename):
    f = open(filename, "r")
    content = f.read()
    f.close()
    return content.strip()

def BroadcastTelegramMessage(content):
    for recipient in telegramUsers.values():
        recipient.sendMessage(content)

def CreateFullStatusMessage():
    output = "📊 Status Report 📊\n"
    working = 0
    for c in clients:
        output = output + "\n" + c.getStatusRow()
        if c.lastStatusCode == 0:
            working+=1
    output = output + f"\n\n{working}/{len(clients)} clients online. Last ping round finished at {lastCheck}"
    return output

def ListenForTelegramMessages(APIKey):
    updateOffset = -1
    url = f"https://api.telegram.org/bot{APIKey}/getUpdates"
    while True:
        params = {
            "limit": 5,
            "offset": updateOffset,
            "timeout": 120
        }
        r = requests.get(url, params)
        if r.status_code == 200:
            updates = r.json()['result']
            if len(updates) != 0:
                for update in updates:
                    updateOffset = update["update_id"] + 1
                    message = update["message"]
                    msgfrom = message["from"]["id"]
                    msgtext = message["text"]
                    HandleTelegramMessage(msgfrom, msgtext)

        elif r.status_code != 304:
            time.sleep(30)
        time.sleep(0.1)

def HandleTelegramMessage(sender, command):
    sender = str(sender)
    if not (sender in telegramUsers.keys()):
        tempUser = TelegramUser(telegramApiKey, sender)
        tempUser.sendMessage("🔒 You are not authenticated to do this. Please add your telegram user ID to the message-recipients.csv file. You can find your user ID by messaging @JsonDumpBot")
        return False
    else:
        if command == "/status":
            message = CreateFullStatusMessage()
        elif command == "/start":
            message = "👋 Hello! Your user is set up to recieve device status updates. Send me /status any time to get a full status report on all devices."
        else:
            message = "😖 Command not supported. Please use /status to get a full status report on all devices."
        telegramUsers[sender].sendMessage(message)

clients = []
clients_object = ReadCSV('clients.csv')
for row in clients_object:
    clients.append(client(row[1], row[0]))
    print("Clients Loaded")

telegramApiKey = ReadTXT('telegram-api-key.txt')
telegramUsers = {}
telegramUsers_object = ReadCSV('message-recipients.csv')
for row in telegramUsers_object:
    tId = str(row[0])
    telegramUsers[tId] = TelegramUser(telegramApiKey, tId)

heartbeatThread = threading.Thread(target=ClientHeartbeat, args=(clients, ping_frequency))
heartbeatThread.start()

messageListenerThread = threading.Thread(target=ListenForTelegramMessages, args=(telegramApiKey,))
messageListenerThread.start()

BroadcastTelegramMessage("Server Online! Ready to send notifications.")
print("Server Ready")
