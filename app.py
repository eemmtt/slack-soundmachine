#Noise Machine Plays sounds based on slack reactions
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App
from dotenv import load_dotenv
import os, logging, time, threading, sqlite3, re


load_dotenv()

logging.basicConfig(level=logging.DEBUG)
### Slack and Modals ###
app = App(token=os.environ["SLACK_BOT_TOKEN"])

### DB Handling ###
SOUND_PATH = os.environ["SOUND_PATH"]
eventQueue = []
userDict = {}

def createUser(user_id):
  #create a new user in userDict
  userDict[user_id] = {
      "menu_view" : {
        "view_id" : "default menu_view view_id",
        "hash" : "default menu_view hash"
      },
      "add_view" : {
        "view_id" : "default add_view view_id",
        "hash" : "default add_view hash"
      },
      "remove_view" : {
        "view_id" : "default remove_view view_id",
        "hash" : "default remove_view hash"
      }
  }

def deleteUser(user_id):
  #delete user from userDict
  del userDict[user_id]
  
def userInitView(user_id, view, view_id, hash):
  #initialize a view for a user
  userDict[user_id][view]["view_id"] = view_id
  userDict[user_id][view]["hash"] = hash

def userUpdateHash(user_id, view, hash):
  #update hash for a view for a user
  userDict[user_id][view]["hash"] = hash

def dbRead():
  #read db and return all data
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  cur.execute("SELECT * FROM reactionSound")
  data = cur.fetchall()
  con.close()
  return data

def dbToPairs():
  #takes in data from db and returns a list of reaction pair tuples
  pairs = []
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  cur.execute("SELECT * FROM reactionSound")
  data = cur.fetchall()
  con.close()
  for r in data:
    pairs.append((r[1],r[2]))
  print(pairs)
  return pairs

def PairsToStringPairs(pairs):
  #takes in a list of reaction pair tuples and returns a formatted string of them all combined
  result = ""
  for p in pairs:
    filename_only = re.search("([\w\-]+)\.mp3", p[1]).group(1)
    result += f"({p[0]},'{filename_only}') "
  
  print(result)
  return result

def PairsToString(pairs):
  #takes in a list of reaction pair tuples and returns a string of the reactions
  result = ""
  for p in pairs:
    result += p[0]
    
  print(result)
  return result

def initReactionString(type):
  if type == "pairs":
    return StringToSection(PairsToStringPairs(dbToPairs()))
  elif type == "reactions":
    return StringToSection(PairsToString(dbToPairs()))
  else:
    print("Bad param to initReactionString, enter 'pairs' or 'reactions'")
    return StringToSection("Error")
  
def StringToSection(text):
  #takes in a string and returns a section block with the string
  section = {
    "type": "section",
    "text": {
      "type": "plain_text",
      "text": text,
      "emoji": True
    }
  }
  return section

def stringValidate_removal(string):
  #check string against regex for removal
  match = re.search("(^:{1}\w+:{1}$)", string)
  if match:
    return match.group()
  else:
    return ""

def errorCheck_removal(input):
  #check capture against error cases, return error message if error
  if input == "":
    return "Error: Invalid input entered"
  elif not dbCheckForReaction(input):
    return "Error: Reaction not found for removal"
  else:
    return ""

def stringValidate_add(string):
  #check string against regex for add
  match = re.findall("(:{1}\w+:{1})(\s+)([\w\-]+)(\.mp3)", string)
  if match:
    return match[0]
  else:
    return ""

def errorCheck_add(input):
  #check capture against error cases, return error message if error
  if input == "":
    return "Error: Invalid input entered"
  elif dbCheckForReaction(input[0]):
    return "Error: Reaction already exists"
  elif not os.path.exists(SOUND_PATH+input[2]+input[3]):
    return f"Error: Sound file not found in {SOUND_PATH}"
  else:
    return ""
  
def dbCheckForReaction(reaction):
  #takes in reaction_added payload and checks if reaction is in db
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  cur.execute("SELECT * FROM reactionSound WHERE reaction=?", (reaction,))
  data = cur.fetchall()
  con.close()
  
  if len(data)>0:
    #print("Reaction found in dbCheck")
    return True
  else:
    #print("Reaction not found in dbCheck")
    return False
  

def dbCheck(reaction):
  #takes in reaction_added payload and checks if reaction is in db
  fReaction = f":{reaction}:"
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  cur.execute("SELECT * FROM reactionSound WHERE reaction=?", (fReaction,))
  data = cur.fetchall()
  con.close()
  if len(data)>0:
    #print("Reaction found in dbCheck")
    return True
  else:
    #print("Reaction not found in dbCheck")
    return False

def dbGetSoundPath(reaction):
  #takes in reaction_added payload and returns associated sound path
  #must run dbCheck first to ensure reaction is in db
  fReaction = f":{reaction}:"
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  cur.execute("SELECT sound FROM reactionSound WHERE reaction=?", (fReaction,))
  data = cur.fetchall()
  con.close()
  #print(data)
  filename = data[0][0]
  path = SOUND_PATH
  return f"{path}{filename}"

from pygame import mixer
mixer.init()

def playReaction(r):
    if dbCheck(r)==True:
      try:
        mixer.music.load(dbGetSoundPath(r))
        mixer.music.play() #Playing Music with Pygame
        
        while mixer.music.get_busy() == True:
          if len(eventQueue) > 0:
            mixer.music.fadeout(1000)
            mixer.music.stop()
          else:
            time.sleep(0.5)
        
        mixer.music.stop()
      except:
        print(f"File path not found for {r}")
    else:
      print(f"no sound found for {r}")

def dbAddPair(reactionSound):
  #add a new pair to the db
  reaction = reactionSound[0]
  sound = reactionSound[1]
  
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  
  cur.execute("SELECT * FROM reactionSound")
  data = cur.fetchall()
  lenData = len(data)
  
  #insert new row with form data
  cur.execute("INSERT OR IGNORE INTO reactionSound(reaction, sound) VALUES (?, ?)", (reaction, sound))
  con.commit()
  
  #count number of rows in table after insert
  cur.execute("SELECT * FROM reactionSound")
  data2 = cur.fetchall()
  lenData2 = len(data2)
  
  #if number of rows increased, confirm success
  if lenData2 > lenData:
    print(f"({reaction},{sound}) Added to DB")
  
  con.close()
  
def dbRemoveReaction(reaction):
  #remove a row from the db
  
  con = sqlite3.connect("reactionSound.db")
  cur = con.cursor()
  
  cur.execute("SELECT * FROM reactionSound")
  data = cur.fetchall()
  lenData = len(data)
  
  #delete the row from db containing reaction
  cur.execute("DELETE FROM reactionSound WHERE reaction = ?", (reaction,))
  con.commit()
  
  #count number of rows in table after insert
  cur.execute("SELECT * FROM reactionSound")
  data2 = cur.fetchall()
  lenData2 = len(data2)
  
  #if number of rows decreased, confirm success
  if lenData2 < lenData:
    print(f"{reaction} removed from DB")
  else:
    print("Error removing reaction")
  
  con.close()

    
def execEvent(event):
  return event[0](event[1])

def eventLoop():
  #check for events in queue and execute them
  while True:
    if len(eventQueue)>0:
      event = eventQueue.pop()
      execEvent(event)
    else:
      time.sleep(0.1)

### Modal Composition Functions ###
def composeMenuView():
  sectionPair = initReactionString("pairs")
  view = {
    "type": "modal",
    "callback_id": "menuView-modal",
    "notify_on_close": True,
    "title": 
    {
      "type": "plain_text",
      "text": "Snolloween Noise Machine",
      "emoji": True
    },
    "close": 
    {
      "type": "plain_text",
      "text": "Close",
      "emoji": True
    },
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "React to a slack message with an emoji to play the corresponding sound on the _Snolloween Noise Machine_ in the front of the NY Office!"
        }
      },
      {
        "type": "divider"
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Registered Reaction/Sound Pairs:*"
        }
      },
      sectionPair,
      {
        "type": "divider"
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "Add a Reaction/Sound Pair"
        },
        "accessory": {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": ":notes::ghost::notes:",
            "emoji": True
          },
          "value": "addPair",
          "action_id": "button-addView"
        }
      },
      {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Remove a Reaction/Sound Pair"
      },
      "accessory": {
        "type": "button",
        "text": {
          "type": "plain_text",
          "text": ":bouquet: :coffin::bouquet:",
          "emoji": True
        },
        "value": "removePair",
        "action_id": "button-removeView"
      }
      }
    ]
  }
  return view

def composeAddView():
  sectionSingle = initReactionString("reactions")
  view={
          "type": "modal",
            "callback_id": "addView-modal",
          "notify_on_close": True,
          "title": {
            "type": "plain_text",
            "text": "Add Pairing",
            "emoji": True
          },
          "submit": {
            "type": "plain_text",
            "text": "Submit",
            "emoji": True
          },
          "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
          },
          "blocks": [
            {
              "type": "divider"
            },
                {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": "*Registered Reactions:*"
              }
            },
            sectionSingle,
            {
              "type": "divider"
            },
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": "*Instructions:*"
              }
            },
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": f"*Step 1:* \nCopy your mp3 to {SOUND_PATH}. \nFile names may only contain letters, numbers, and underscores. \nMultiple emoji may use the same sound file."
              }
            },
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": "*Step 2:* \nInput your desired emoji and mp3 filename below, seperated by a space. \nInput must match example format _exactly_."
              }
            },
            {
              "dispatch_action": False,
              "type": "input",
              "block_id": "input-block",
              "element": {
                "type": "plain_text_input",
                "initial_value": ":emojiName: yourSoundFileName.mp3",
                "action_id": "addPair-action"
              },
              "label": {
                "type": "plain_text",
                "text": " ",
                "emoji": True
              }
            }
          ]
        }
  return view

def composeRemoveView():
  sectionSingle = initReactionString("reactions")
  view={
          "type": "modal",
          "callback_id": "removeView-modal",
          "notify_on_close": True,
          "title": {
            "type": "plain_text",
            "text": "Remove Pairing",
            "emoji": True
          },
          "submit": {
            "type": "plain_text",
            "text": "Finish",
            "emoji": True
          },
          "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
          },
          "blocks": [
            {
              "type": "divider"
            },
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": "*Registered Reactions:*"
              }
            },
            sectionSingle,
            {
              "type": "divider"
            },
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": "*Input the emoji you'd like to remove:*"
              }
            },
            {
              "dispatch_action": False,
              "type": "input",
              "block_id": "input-block",
              "element": {
                "type": "plain_text_input",
                "initial_value": ":emojiName:",
                "action_id": "removePair-action"
              },
              "label": {
                "type": "plain_text",
                "text": " ",
                "emoji": True
              }
            }
          ]
        }
  return view

def composeHomeView():
  sectionPair = initReactionString("pairs")
  view = {
    "type": "home",
    "callback_id": "home_view",
    "title": 
    {
      "type": "plain_text",
      "text": "Snolloween Noise Machine",
      "emoji": True
    },
    "blocks": [
      {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "Snolloween Noise Machine",
				"emoji": True
			}
		  },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "React to a slack message with one of the emojis below to play the corresponding sound on the _Snolloween Noise Machine_ in the front of the NY Office!"
        }
      },
      {
        "type": "divider"
      },
      {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "Reaction/Sound Pairs:",
				"emoji": True
			}
		  },
      sectionPair,
      {
        "type": "divider"
      },
      {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "FAQ:",
				"emoji": True
			}
		  },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Q:* How do I add a reaction/sound pair?\n*A:* Type \"/snolloween\" into any Channel or Direct Message. \"/snolloween\" cannot be used in reply threads."
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Q:* How do I remove a reaction/sound pair?\n*A:* Type \"/snolloween\" into any Channel or Direct Message. \"/snolloween\" cannot be used in reply threads."
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": f"*Q:* What kind of sounds can i use?\n*A:* Sound files must be .mp3's. Longer sounds will likely be cutoff. Sound files must be uploaded to {SOUND_PATH}."
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Q:* Where can I get sound files?\n*A:* You can get them anywhere; creating/editing sound is beyond the scope of this FAQ.\n     Try https://freesound.org/\n"
        }
      },
      
    ]
  }
  return view


### Log Middleware ###
@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    next()


### Slash Commands ###
@app.command("/snolloween")
def handle_command(body, ack, client, logger):
    logger.info(body)
    ack()
    
    res = client.views_open(
        trigger_id=body["trigger_id"],
        view= composeMenuView()
    )
    
    createUser(body["user_id"])
    userInitView(body["user_id"], "menu_view", res["view"]["id"], res["view"]["hash"])
    
    logger.info(res)


### Menu Events ###
@app.view_closed("menuView-modal")
def menuView_closed(ack, body, client, logger):
    ack()
    logger.info(body["view"]["state"]["values"])
    
    try:
      client.views_publish(
        user_id=body["user"]["id"],
        view=composeHomeView()
      )
    except Exception as e:
      logger.error(f"Error publishing home tab: {e}")
    
    deleteUser(body["user"]["id"])

@app.action("button-addView")
def addView_push(ack, client, body, logger):
    logger.info(body)
    ack()

    res = client.views_push(
        trigger_id=body["trigger_id"],
        view=composeAddView()
    )
    logger.info(res)
    
    userInitView(body["user"]["id"], "add_view", res["view"]["id"], res["view"]["hash"])
    
@app.action("button-removeView")
def removeView_push(ack, client, body, logger):
    logger.info(body)
    ack()

    res = client.views_push(
        trigger_id=body["trigger_id"],
        view=composeRemoveView()
    )
    logger.info(res)
    userInitView(body["user"]["id"], "remove_view", res["view"]["id"], res["view"]["hash"])

### Add View Events ###
@app.view("addView-modal")
def addView_submission(ack, body, client, logger):
    logger.info(body["view"]["state"]["values"])
    
    input = body["view"]["state"]["values"]["input-block"]["addPair-action"]["value"]
    match = stringValidate_add(input)
    print(match)
    error = errorCheck_add(match)
    
    if error:
      myError = {}
      myError["input-block"] = error
      ack(response_action="errors", errors=myError)
      return
    else:
      ack()
      #eventQueue.append((dbRemoveReaction, match))
      matchFormatted = (match[0], match[2]+match[3])
      dbAddPair(matchFormatted)
      res = client.views_update(
          view_id=userDict[body["user"]["id"]]["menu_view"]["view_id"],
          view=composeMenuView()
      )
      return
    
@app.view_closed("addView-modal")
def addView_closed(ack, body, client, logger):
    ack()
    logger.info(body)
    res = client.views_update(
        view_id=userDict[body["user"]["id"]]["menu_view"]["view_id"],
        view=composeMenuView()
    )
    return
    
### Remove View Events ###
@app.view("removeView-modal")
def removeView_submission(ack, body, client, logger):
    #logger.info(body["view"]["state"]["values"])
    input = body["view"]["state"]["values"]["input-block"]["removePair-action"]["value"]
    print(input)
    match = stringValidate_removal(input)
    print(match)
    error = errorCheck_removal(match)
    
    if error:
      myError = {}
      myError["input-block"] = error
      ack(response_action="errors", errors=myError)
      return
    else:
      ack()
      #eventQueue.append((dbRemoveReaction, match))
      dbRemoveReaction(match)
      res = client.views_update(
          view_id=userDict[body["user"]["id"]]["menu_view"]["view_id"],
          view=composeMenuView()
      )
      return

@app.view_closed("removeView-modal")
def removeView_closed(ack, body, client, logger):
    ack()
    logger.info(body)
    res = client.views_update(
        view_id=userDict[body["user"]["id"]]["menu_view"]["view_id"],
        view=composeMenuView()
    )
    return

### Home View Events ###
@app.event("app_home_opened")
def update_home_tab(client, event, logger):
  try:
    client.views_publish(
      user_id=event["user"],
      view=composeHomeView()
    )
  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")

@app.action("action-launchEditor")
def homeButton_handler(ack, client, body, logger):
    logger.info(body)
    ack()
    
    res = client.views_open(
        trigger_id=body["trigger_id"],
        view= composeMenuView()
    )
    
    createUser(body["view"]["id"])
    userInitView(body["view"]["id"], "menu_view", res["view"]["id"], res["view"]["hash"])
    
    logger.info(res)

@app.event("reaction_added")
def handle_reaction(ack, event):
    ack()
    r = event["reaction"]
    eventQueue.append((playReaction, r))   


# Start your app
if __name__ == "__main__":
    
    tr = threading.Thread(target=eventLoop, args=())
    tr.start()
    
    #socket host app start
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()            
    