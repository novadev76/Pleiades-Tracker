import logging
import discord
import os
from dotenv import load_dotenv
import a2s
from datetime import datetime
import re
import mysql.connector
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

load_dotenv()

mydb = mysql.connector.connect(
    host = "localhost",
    user = str(os.getenv('SQLUSER')),
    password = str(os.getenv('SQLPASSWORD')),
    database = "testing_schema"
)

cur = mydb.cursor()

bot_token = str(os.getenv('TOKEN'))

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot()

def is_me(m):
    return m.author == bot.user

async def track(): 
    print("Function got ran!")
    query = "SELECT channelID FROM channeltoserver"
    cur.execute(query)
    channelIDList = cur.fetchall()
    if channelIDList is None or channelIDList[0] == '':
        print("There was no channels present in the database!")
        pass
    else:
        for channelResponse in channelIDList:
            print("first for loop entered!")
            channelID = int(channelResponse[0])
            channel = await bot.fetch_channel(channelID)
            await channel.purge(limit=100, check=is_me)
            val = (channelResponse[0],)
            query = "SELECT servers FROM channeltoserver WHERE channelID = %s"
            cur.execute(query, val)
            serversJSON = cur.fetchone()
            if serversJSON[0] is None:
                print(f"There were nothing present in the servers field for {channelResponse}")
                pass
            else:
                servers = json.loads(serversJSON[0])
                serversValues = servers.get("servers")
                if serversValues is None:
                    print(f"There was nothing present in the JSON file for {channelResponse}!")
                for serverIP in serversValues:                            #I AM AWARE THAT I HAVE REUSED THE BELOW CODE. I AM LAZY. YES I PLAN TO MAKE IT A SEPERATE FUNCTION. I WILL DO IT LATER!!!!!!!!!!!!!!
                    print("second for loop entered!")
                    serverSplit = serverIP.split(":")
                    serverAddress = str(serverSplit[0])
                    serverPort = int(serverSplit[1])
                    address = (serverAddress, serverPort)
                    try:
                        serverInfo = a2s.info(address) # figure out how to properly implement the async version of this later
                        serverInfoSplit = str(serverInfo).split(",")

                        serverNameUnclean = serverInfoSplit[1]
                        serverMapUnclean = serverInfoSplit[2]
                        serverCurrentUnclean = serverInfoSplit[6]
                        serverMaxUnclean = serverInfoSplit[7]

                        serverNameClean = clean_string(str(serverNameUnclean))
                        serverMapClean = str(serverMapUnclean).replace("map_name='", '').strip("'")
                        serverCurrentClean = str(serverCurrentUnclean).replace("player_count=", '')
                        serverMaxClean = str(serverMaxUnclean).replace("max_players=", '')
                        serverPlayers = (f"{serverCurrentClean}/{serverMaxClean}").replace(" ", "")
                    

                        serverJoin = f"[{str(serverIP)}](REDACTED)" 

                        embed = discord.Embed(
                            title=serverNameClean,
                            description=f"Now Playing: **{serverMapClean}**\nPlayers Online: **{serverPlayers}**\nQuick Join: **{serverJoin}**",
                            timestamp=datetime.now()
                        )

                        await channel.send(embed=embed)
                    except:
                        print("tracker screwed up")
                        await channel.send("An error occured when attempting to retrieve the server information. Please try again later! If the error persists, contact the bot creator!")
                else:
                    print(f"The servers for {channelResponse} have been tracked!")
                    pass
        else:
            print("All channels have had their servers tracked!")


def clean_string(input_str):      #the most scuffed implementation imaginable, but it works. Don't know why it refuses to clean \x01 so I had to physically split the string.
    chars_to_remove = '\x01⤳⬿'
    input_str = input_str.split("⤳")
    translation_table = str.maketrans('', '', chars_to_remove)
    cleaned_str = input_str[1].translate(translation_table)
    cleaned_str = cleaned_str.replace("server_name=", "").replace("'", "")
    cleaned_str = re.sub("\x01", "", cleaned_str)
    return cleaned_str
    
@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.slash_command(guild_ids=[1068433342812389436])
async def test(ctx):
    query = "SELECT channelID FROM channeltoserver"
    cur.execute(query)
    channelIDList = cur.fetchall()
    x = 0
    await ctx.respond(str(channelIDList[x][0]))


@bot.slash_command(guild_ids=[1068433342812389436])
async def hello(ctx):
    await ctx.respond("Gday mate, you suck!")

@bot.slash_command(guild_ids=[1068433342812389436])
async def retrieve(ctx, server):
    try:
        serverSplit = server.split(":")
        serverIP = str(serverSplit[0])
        serverPort = int(serverSplit[1])
    except: 
        await ctx.respond("An error occured, are you sure you put in a correct server address?")

    address = (serverIP, serverPort)

    try:            #I AM AWARE THAT I HAVE REUSED THE BELOW CODE. YES I PLAN TO MAKE IT A SEPERATE FUNCTION. I WILL DO IT LATER!!!!!!!!!!!!!!
        serverInfo = a2s.info(address) # figure out how to properly implement the async version of this later
        serverInfoSplit = str(serverInfo).split(",")

        serverNameUnclean = serverInfoSplit[1]
        serverMapUnclean = serverInfoSplit[2]
        serverCurrentUnclean = serverInfoSplit[6]
        serverMaxUnclean = serverInfoSplit[7]

        serverNameClean = clean_string(str(serverNameUnclean))
        serverMapClean = str(serverMapUnclean).replace("map_name='", '').strip("'")
        serverCurrentClean = str(serverCurrentUnclean).replace("player_count=", '')
        serverMaxClean = str(serverMaxUnclean).replace("max_players=", '')
        serverPlayers = (f"{serverCurrentClean}/{serverMaxClean}").replace(" ", "")
        

        serverJoin = f"[{str(server)}](REDACTED)" 

        embed = discord.Embed(
            title=serverNameClean,
            description=f"Now Playing: **{serverMapClean}**\nPlayers Online: **{serverPlayers}**\nQuick Join: **{serverJoin}**",
            timestamp=datetime.now()
        )

        await ctx.respond(embed=embed)
    except:
        await ctx.respond("An error occured when attempting to retrieve the server information. Please try again later! If the error persists, contact the bot creator!")

@bot.slash_command(guild_ids=[1068433342812389436])
async def addchannel(ctx, channel_id):
    try:
        cleanChannelID = int(channel_id)
        val = (cleanChannelID,)
        query = "INSERT INTO channeltoserver (channelID) VALUES (%s)"
    
        try:
            cur.execute(query, val)

            mydb.commit()
            await ctx.respond(f"The channel with an ID of {cleanChannelID} was added to the database!")
        except:
            await ctx.respond("Error occured, the channel may already be saved in the database. If you are sure this is not the case, contact the bot creator.")
    except:
        await ctx.respond("Are you sure you inserted a channel ID?")

@bot.slash_command(guild_ids=[1068433342812389436])
async def removechannel(ctx, channel_id):
    try:
        cleanChannelID = int(channel_id) # checks if it is an INT and not just full of random letters
        val = (cleanChannelID,)
        testQuery = "SELECT channelID FROM channeltoserver WHERE channelID = (%s)"

        try:
            cur.execute(testQuery, val)
            response = str(cur.fetchall())
            if response == "[]":
                await ctx.respond("The channel ID provided doesn't exist in the database!")
            else:
                deleteQuery = "DELETE FROM channeltoserver WHERE channelID = (%s)"
                cur.execute(deleteQuery, val)
                mydb.commit()
                await ctx.respond(f"The channel ID of {cleanChannelID} has been unlinked from the database!")
        except:
            await ctx.respond("An error occured when trying to determine if the channel ID was already in the database. Contact the bot creator if this persists!")    
    except:
        await ctx.respond("Are you sure you inserted a channel ID?")

@bot.slash_command(guild_ids=[1068433342812389436])
async def thejokeu(ctx):
    await ctx.respond("https://i.imgur.com/lwEKkud.jpeg")

@bot.slash_command(guild_ids=[1068433342812389436])
async def addserver(ctx, channel_id, server_ip):
    channel_idVal = (channel_id,)
    query = "SELECT channelID FROM channeltoserver WHERE channelID = (%s)"
    cur.execute(query, channel_idVal)
    channelResult = cur.fetchone()

    if channelResult is None or channelResult[0] == '':
        await ctx.respond("The channelID entered does not currently exist within the database!")
    else:
        query = "SELECT servers FROM channeltoserver WHERE channelID = (%s)"
        cur.execute(query, channel_idVal)
        serverResult = cur.fetchone()
        if serverResult[0] is None:
            servers = {
                "servers": [
                    server_ip
                ]
            }                                                                   
            data = json.dumps(servers)
            val = (data, channel_id)
            query = "UPDATE channeltoserver SET servers = (%s) WHERE channelID = (%s)"
            cur.execute(query, val)
            mydb.commit()
            await ctx.respond("The server has been linked and will start to track in the specified channel!")
        else:
            serverResult = serverResult[0]
            servers = json.loads(serverResult)
            serversValues = servers.get("servers")
            if server_ip in serversValues:
                await ctx.respond("The server is already linked to this channel!")
            else:
                servers["servers"].append(server_ip)
                data = json.dumps(servers)
                val = (data, channel_id)
                query = "UPDATE channeltoserver SET servers = (%s) WHERE channelID = (%s)"
                cur.execute(query, val)
                mydb.commit()
                await ctx.respond("The server has been linked and will start to track in the specified channel!")


@bot.slash_command(guild_ids=[1068433342812389436])
async def removeserver(ctx, channel_id, server_ip):
    val = (channel_id,)
    query = "SELECT channelID FROM channeltoserver WHERE channelID = (%s)"
    cur.execute(query, val)
    channelResult = cur.fetchone()
    
    if channelResult is None or channelResult[0] == '':
        await ctx.respond("The channelID entered does not currently exist within the database!")
    else:
        query = "SELECT servers FROM channeltoserver WHERE channelID = (%s)"
        cur.execute(query, val)
        serverResult = cur.fetchone()
        if serverResult is None or channelResult[0] == '':
            await ctx.respond("There are currently no servers linked to the channel ID mentioned.")
        else:
            serverResult = serverResult[0]
            servers = json.loads(serverResult)
            serversValues = servers.get("servers")
            if server_ip in serversValues:
                servers["servers"].remove(server_ip)
                data = json.dumps(servers)
                val = (data, channel_id)
                query = "UPDATE channeltoserver SET servers = (%s) WHERE channelID = (%s)"
                cur.execute(query, val)
                mydb.commit()
                await ctx.respond("The server has been unlinked from the channel!")
            else:
                await ctx.respond("The server mentioned was not linked to the channel!")

@bot.event
async def on_ready():
    print("Async schedule is initialising!")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(track, 'interval', minutes=1)
    scheduler.start()
    print("Async schedule has started!")


bot.run(bot_token)
