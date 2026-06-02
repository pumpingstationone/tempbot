#!/usr/bin/env python3

import threading
import collections
import json
import configparser
import paho.mqtt.client as mqtt

import discord
from discord.ext import commands

##########################################################################################
## Configuration
##########################################################################################

config = configparser.ConfigParser()
config.read("config.ini")

##########################################################################################
## Discord fun
##########################################################################################

intents = discord.Intents.all()

# Create an instance of a bot
bot = commands.Bot(description="Temp Bot", command_prefix="!", intents=intents)


# This is where we build the text that will be sent back to the requestor.
def build_response(request):
    # This sub-function will loop through the array and return the first element
    # value where the length of the string is greater than 0
    def find_area(parts_array):
        for part in parts_array:
            if len(part) > 0:
                return part
        return ""

    def build_help_text():
        help_response = "Hmm, you want to enter `!temp <area>` (case insensitive).\n_I currently know of the following areas:_ "
        # Now get all the areas we know about
        areas = list(temp_dict.data.keys())
        area_text = ""
        for area in areas:
            area_text += f"`{area}`,"

        # And, uh, remove the last comma
        help_response += area_text[:-1]
        help_response += (
            "\nYou can also type `!temp all` to get the temperatures in all areas"
        )
        return help_response

    def build_temp_text(area_requested):
        # This is the function that we use to build the response that
        # will have the temperature and humidty, that we'll format in
        # both fahrenheit and celsius
        def format_temp(stored_area, temp_json):
            # Your standard conversion...
            def celsius_to_fahrenheit(celsius):
                fahrenheit = (celsius * 9 / 5) + 32
                # And round our calculation to a whole number
                return round(fahrenheit)

            # Get our values...
            cel_temp = temp_json["temperature"]
            fah_temp = celsius_to_fahrenheit(cel_temp)
            humidity = temp_json["humidity"]

            # And now let's build our string
            area_temp_text = f"The temperature in `{stored_area}` is *{fah_temp}* F (*{cel_temp}* C). The humidty is *{humidity}*."

            return area_temp_text

        # Okay, we have an area, but is that a _real_ area or gibberish?
        temp_text = ""

        # Let's go through the keys to see if we can find what they asked for
        areas = list(temp_dict.data.keys())
        for area in areas:
            # Special ... if they want everything, we build that here
            if area_requested == "all":
                temp_text += format_temp(area, temp_dict[area])
                # And get ready for the next line
                temp_text += "\n"
            # Did we find the specific area?
            elif area == area_requested:
                # Ah, we did, so we'll build the response by
                # formatting the json that holds the temperature,
                # humidity, etc.
                temp_text = format_temp(area, temp_dict[area])

        # Did we find the appropriate area?
        if len(temp_text) == 0:
            # No we didn't, so we'll give them the help text.
            temp_text = build_help_text()

        return temp_text

    print(f"Got this request: {request}")

    # This is what we're gonna send back
    response = ""

    # First let's see if the request contains a specific area or the magic word "all"
    # We split on the space and get an array of parts we're going to work with
    req_parts = request.split(" ")
    # req_parts[0] is the trigger word ('!temp').
    # We may or may not have another word after the trigger word, and
    # we don't know how many spaces are between element 0 and the word.
    # Soooo we have a sub-function that looks to see if we can find
    # something. _If_ we do find a word, we'll try to find that in the
    # dictionary. Otherwise, if we can't find the word, or there's nothing,
    # we'll return the help text
    area = find_area(req_parts[1:])

    # Now let's see if we even have anything to work with
    if len(area) == 0:
        # Nope, so let's give them the help text
        response = build_help_text()
    else:
        # Ah, we _do_ have something, but we don't know if this is
        # something we can work with, so we may still end up sending
        # the help text
        response = build_temp_text(area)

    return response


# Define a command
@bot.command(name="temp")
async def hello_world(ctx):
    # Get the message that was sent to us
    request = ctx.message.content
    # And build the response
    response = build_response(request)
    # And send it back
    await ctx.send(response)


##########################################################################################
## Our thread-safe dictionary
##########################################################################################


class TempDict:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {}

    def __getitem__(self, key):
        with self.lock:
            return self.data[key]

    def __setitem__(self, key, value):
        with self.lock:
            self.data[key] = value

    def __len__(self):
        with self.lock:
            return len(self.data)


# This is the actual dictionary we're going to populate
temp_dict = TempDict()


##########################################################################################
## MQTT Section
##########################################################################################


# Maps THS sensor IDs to human-readable area names
SENSOR_AREAS = {
    "THS-Woodshop-01":    "Woodshop",
    "THS-SmallMetals-01": "Small Metals",
    "THS-ServerRoom-01":  "Server Room",
    "THS-Lounge-01":      "Lounge",
    "THS-Kitchen-01":     "Kitchen",
    "THS-HotMetals-01":   "Hot Metals",
    "THS-General-01":     "General",
    "THS-Entryway-01":    "Entryway",
    "THS-Electronics-01": "Electronics",
    "THS-Dock-01":        "Dock",
    "THS-ColdMetals-01":  "Cold Metals",
    "THS-CNC-01":         "CNC",
    "THS-Catwalk-01":     "Catwalk",
    "THS-BoilerRoom-01":  "Boiler Room",
    "THS-Arts-01":        "Arts",
}


# This function is invoked by the MQTT library when we get
# a message
def on_message(client, userdata, message):
    try:
        # Topic format: ps1/zigbee2mqtt/THS-<Area>-01
        sensor_id = message.topic.split("/")[-1]
        if sensor_id not in SENSOR_AREAS:
            return

        area = SENSOR_AREAS[sensor_id]
        payload = json.loads(message.payload.decode())
        temp_dict[area] = payload

        print(f"AREA: {area} ==> {temp_dict[area]}")
    except Exception as e:
        print(f"Got a message error: {str(e)}")


def setup_mqtt_reader():
    # Initialize the MQTT client
    client = mqtt.Client()
    client.connect(config["MQTT"]["broker"], int(config["MQTT"]["port"]))

    # Subscribe to the MQTT topic
    client.subscribe(config["MQTT"]["topic"])

    # Add the message callback function to the MQTT client
    client.on_message = on_message

    # Start the MQTT client loop to receive messages
    client.loop_forever()


##########################################################################################
## Program begins here
##########################################################################################

# First we're gonna set up the thread that reads from the MQTT topics
print("Starting the mqtt thread...")
mqtt_reader_thread = threading.Thread(target=setup_mqtt_reader)
mqtt_reader_thread.start()

# And listen on the mqtt topic forever...
# mqtt_reader_thread.join()

# Now let's set up the Discord part
print("Starting the Discord thread...")
# Run the bot
bot.run(config["Discord"]["token"])
