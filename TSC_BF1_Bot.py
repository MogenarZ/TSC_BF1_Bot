import requests, bs4, sys, re, plotly, os, operator, shutil, discord
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from dotenv import load_dotenv
import plotly.io as pio
#pio.orca.config.use_xvfb = True
#plotly.io.orca.config.executable = r"C:\Users\Alexander\AppData\Local\Programs\orca\orca.exe"
plotly.io.orca.config.executable = "/opt/orca/squashfs-root/app/orca"

#####GLOBAL
bf1_classes = ["Tanker/Pilot", "Assault", "Medic", "Support", "Scout", "Elite", "Vehicle", "All"]

smgs = ["MP 18", "Automatico M1918", "Hellriegel 1915", "Annihilator", "M1919 SMG", "Ribeyrolles 1918", "SMG 08/18", "M1917 Trench Carbine", "Maschinenpistole M1912/P.16", "RSC SMG"]
shotguns = ["M97 Trench Gun", "Model 10-A", "12g Automatic", "Sjögren Inertial", "Model 1900"]
sl_rifles = ["Cei-Rigotti", "Selbstlader M1916", "M1907 SL", "Mondragón", "Autoloading 8 .35", "Autoloading 8 .25", "Selbstlader 1906", "Fedorov-Degtyarev", "RSC 1917", "Fedorov Avtomat", "General Liu Rifle", "Farquhar-Hill", "Howell Automatic"]
lmgs = ["Lewis Gun", "M1909 Benét–Mercié", "Madsen MG", "MG15 n.A.", "BAR M1918", "Huot Automatic", "BAR M1918A2", "Burton LMR", "Chauchat", "Parabellum MG14/17", "Perino Model 1908", "M1917 MG", "lMG 08/18"]
sa_rifles = ["SMLE MKIII", "Gewehr 98", "Russian 1895", "Gewehr M.95", "M1903", "Martini-Henry", "Mosin-Nagant M38", "Lebel Model 1886", "Mosin-Nagant M91", "Vetterli-Vitali M1870/87", "Carcano M91", "Type 38 Arisaka",
            "Ross MkIII", "M1917 Enfield"]
carbine_pistols = ["C96 Carbine", "Frommer Stop Auto", "M1911 Extended", "Pieper M1893", "P08 Artillerie", "Mle 1903 Extended", "C93 Carbine", "Sawed Off Shotgun"]
pistols_all = ["M1911", "P08 Pistol", "Mle 1903", "No. 3 Revolver", "C93", "Kolibri", "M1911A1", "Peacekeeper", "Nagant Revolver", "Obrez Pistol", "Revolver Mk VI"]
pistols_assault = ["Gasser M1870", "1903 Hammerless", "Howdah Pistol"]
pistols_medic = ["Auto Revolver", "Taschenpistole M1914", "C96"]
pistols_support = ["Bull Dog Revolver", "Modello 1915", "Repetierpistole M1912"]
pistols_scout = ["Bodeo 1889", "Frommer Stop", "Mars Automatic"]
elite_weapons = ["Wex", "MG 08/15", "Villar Perosa", "Tankgewehr M1918", "Martini-Henry Grenade Launcher"]

gear_assault = ["Anti-Tank Grenade", "Anti-Tank Mine", "AT Rocket Gun", "Dynamite", "AA Rocket Gun"]
gear_medic = ["Rifle Grenade"]
gear_support = ["Limpet Charge", "Mortar", "Repair Tool", "Crossbow Launcher"]
gear_scout = ["K Bullet", "Flare Gun", "Tripwire Bomb"]

suffixes = ["Patrol Carbine", "Factory", "Trench", "Storm", "Optical", "Marksman", "Sniper", "Backbored", "Hunter", "Slug", "Extended", "Low Weight", "Telescopic", "Suppressive", "Infantry", "Carbine", "Sweeper", "Experimental", "Defensive", "Cavalry",
            "Silenced", "Silencer", "Patrol", "— FRG", "— INC", "— HE", "— AIR", "— GAS"]

tanks = ["Landship", "Assault Tank", "Artillery Truck", "Heavy Tank", "Light Tank", "Assault Truck"]
planes = ["Heavy Bomber", "Attack Plane", "Airship", "Bomber", "Fighter"]

					
weapons_by_class = {wep:"Assault" for wep in smgs + shotguns + pistols_assault + gear_assault}
weapons_by_class.update({wep:"Medic" for wep in sl_rifles + pistols_medic + gear_medic})
weapons_by_class.update({wep:"Support" for wep in lmgs + pistols_support + gear_support})
weapons_by_class.update({wep:"Scout" for wep in sa_rifles + pistols_scout + gear_scout})
#carbine pistols processed separately because they have to be done first
#weapons_by_class.update({wep:"Tanker/Pilot" for wep in carbine_pistols})
weapons_by_class.update({wep:"Elite" for wep in elite_weapons})
weapons_by_class.update({wep:"All" for wep in pistols_all})

rec_x = 500
rec_y = 500



#####FUNCTIONS
def read_bf1tracker_stats(username):
    """basic parsing of user's frontpage on BF1Tracker"""
    r = requests.get("https://battlefieldtracker.com/bf1/profile/pc/"+username)
    return bs4.BeautifulSoup(r.text, "html.parser")
    for tag in [tag for tag in web_data.find_all("div") if tag.attrs.get("class", "crap") == ["stats-large"]]:
        print(tag)

###BF1 stats doesn't have DLC vehicle info
def read_bf1tracker_data(username, vehicles):
    """pulls vehicle or weapon information from BF1Tracker"""
    if vehicles:
        r = requests.get("https://battlefieldtracker.com/bf1/profile/pc/"+username+"/vehicles")
        web_data = bs4.BeautifulSoup(r.text, "html.parser")
        tbody = web_data.find("tbody").findAll("tr")
    else:
        r = requests.get("https://battlefieldtracker.com/bf1/profile/pc/"+username+"/weapons")
        web_data = bs4.BeautifulSoup(r.text, "html.parser")
        tbody = web_data.findAll("tbody")[1].findAll("tr")  

    stuff_info = []
    for piece in tbody:
        if piece.findAll("td")[0].findAll("div") != []:
            #print(piece.findAll("td")[0].findAll("div"))
            name = piece.find("td").find("div").text.strip()
            kills = piece.findAll("td")[1].find("div").text
            thing_class = False
            if vehicles:
                name = name.title()
                thing_class = "Vehicle"
            else:
                ###this is where it gets complicated
                ###tanker first!
                if name in carbine_pistols:
                    thing_class = "Tanker/Pilot"
                ###this guy's weird
                elif name in ["M1917 Trench Carbine", "M1917 Patrol Carbine"]:
                    thing_class = "Assault"
                else:
                    for suffix in suffixes:
                        if name.endswith(suffix):
                            thing_class = weapons_by_class[name.replace(suffix, "").strip()]
                            break	
            
            ###elites and unlisted weapons
            if not thing_class:
                thing_class = weapons_by_class.get(name, "All")

            stuff_info.append({"name":name, "kills":int(kills.replace(",", "")), "class":thing_class})
    return pd.DataFrame(stuff_info)

def bf1_draw_image(image_path, image_text, font_size):
    """draw image with overlaid text"""
     ###Initialize image magic
    #https://haptik.ai/tech/putting-text-on-image-using-python/
    #image = Image.open(r'C:\Users\Alexander\Pictures\ww1_test.png')
    image = Image.open(image_path)
    image = image.convert("RGBA")

    ###rectangle drawing setup
    #print(image.size)
    tint_color = (0, 0, 0)
    opacity = int(255*0.5)
    image_x, image_y = image.size
    rec_margin_x = 50
    rec_margin_y = 50

    ###draw rectangle
    #https://stackoverflow.com/questions/43618910/pil-drawing-a-semi-transparent-square-overlay-on-image
    overlay = Image.new('RGBA', image.size, tint_color+(0,))
    draw = ImageDraw.Draw(overlay)  # Create a context for drawing things on it.
    draw.rectangle([(rec_margin_x, rec_margin_y), (image_x - rec_margin_x, image_y - rec_margin_y)], fill = tint_color + (opacity,))
    image = Image.alpha_composite(image, overlay)
    image = image.convert("RGB") # Remove alpha for saving in jpg format.

    ###now add text
    draw = ImageDraw.Draw(image)
    #font = ImageFont.truetype(r'C:\Users\Alexander\Desktop\fonts\TravelingTypewriter.ttf', size=30)
    font = ImageFont.truetype('fonts/TravelingTypewriter.ttf', size=font_size)
    #https://stackoverflow.com/questions/1970807/center-middle-align-text-with-pil
    w, h = draw.textsize(image_text, font = font)
    draw.text(((image_x-w)/2,(image_y-h)/2), image_text, fill="white", font=font, align = "center")
    return image

def get_general_stats(username, rank, stats_sections):
    """pulls basic overview stats from bf1stats"""

    ###create big dictionary with all info
    user_info = {"Rank": rank}
    #https://www.geeksforgeeks.org/python-merging-two-dictionaries/
    user_info.update({section.findAll("div")[0].text.strip():section.findAll("div")[1].text.strip().replace(",","") for section in stats_sections if section.find("div")})
    user_info["Rounds"] = int(user_info["Wins"]) + int(user_info["Losses"])

    image_text = username + "\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Rank", "Score/Min", "Kills/Min"]]) + "\n\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Rounds", "Wins", "Losses"]]) + "\n\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Kills", "Deaths", "K/D Ratio", "Headshots", "Accuracy"]])
    
    
    image = bf1_draw_image("images/stats_bg/ww1_test.png", image_text, 30)
    image.save("images/basic_stats_"+username+".png", "PNG")
    return "images/basic_stats_"+username+".png"


def top_10_weapons(username, use_vehicles):
    """graphs user's top 10 weapons"""
    
    weapons_frame = read_bf1tracker_data(username, False)

    ###include vehicles if desired
    if use_vehicles:
        weapons_frame = pd.concat([weapons_frame, read_bf1tracker_data(username, True)], sort = False)
        filename = "images/top_10_"+username+".png"
        plot_title = username + ' : Top 10 by Kills'
    else:
        filename = "images/top_10_weapons_"+username+".png"
        plot_title = username + ' : Top 10 Weapons by Kills'

    weapons_top_10 = weapons_frame.sort_values(by=["kills"], ascending = False).reset_index(drop=True).head(10)[["name","kills","class"]]

    ###determine color of bars based on class
    #https://stackoverflow.com/questions/16476924/how-to-iterate-over-rows-in-a-dataframe-in-pandas
    #colors = [px.colors.sequential.Viridis[bf1_classes.index(row["class"])] for index, row in weapons_top_10.iterrows()]
    #print(colors)

    ###figure time
    #fig = px.bar(weapons_top_10, x='name', y='kills', labels = {"name":"Weapon", "kills":"Kills"})
    fig = go.Figure()
    for bf1_class in sorted(list(set(weapons_top_10["class"]))):
        class_weapons = weapons_top_10[weapons_top_10["class"] == bf1_class]
        fig.add_trace(
            go.Bar(
            x=class_weapons["name"],
            y=class_weapons["kills"],
            marker = dict(color=px.colors.sequential.Viridis[bf1_classes.index(bf1_class)]),
            name = bf1_class
        ))
    fig.update_layout(title_text=plot_title,
                        showlegend = True,
                        xaxis = {
                            'categoryorder': 'array',
                            'categoryarray': list(weapons_top_10["name"])
                        }
    )
    #print(fig)
    #fig.show()
        
    
    fig.write_image(filename)
    return filename

def tsc_server_data():
    """gets player count and current map of TSC server"""
    r = requests.get("https://battlefieldtracker.com/bf1/servers/pc/4567409020989")
    #https://stackoverflow.com/questions/29688440/python-beautiful-soup-ascii-codec-cant-encode-character-u-xa5
    page_text = r.text.encode('utf-8').decode('ascii', 'ignore')
    web_data = bs4.BeautifulSoup(page_text, "html.parser")
    #https://stackoverflow.com/questions/19128523/accessing-non-consecutive-elements-of-a-list-or-string-in-python/19128597#19128597
    summary_tag, rotation_tag = operator.itemgetter(32, 48)(web_data.findAll("div"))

    sub_tags = summary_tag.findAll("div")
    ###players
    player_text = sub_tags[0].findAll("span")[1].text
    #print(player_text)
    ###map
    map_text = sub_tags[2].findAll("span")[1].text.replace("upków", "Lupków")
    #map_text = "Prise de Tahure"
    #print(map_text)

    #for map_tag in rotation_tag.findAll("div"):
       #print(map_tag.find("span").text.replace("upków", "Lupków")+"\n"+map_tag.find("img").attrs["src"])

    ###make sure we have the map image
    map_base = map_text.lower().replace(" ", "_")
    if map_base+".png" not in os.listdir("images/maps"):
        for map_tag in rotation_tag.findAll("div"):
            if map_tag.find("span").text.replace("upków", "Lupków") == map_text:
                ###get image
                r_img = requests.get(map_tag.find("img").attrs["src"], stream=True)
                with open("images/maps/"+map_base+".jpg", "wb") as img_file:
                    shutil.copyfileobj(r_img.raw, img_file)
                ###convert image to png
                #https://stackoverflow.com/questions/10759117/converting-jpg-images-to-png
                map_img = Image.open("images/maps/"+map_base+".jpg")
                map_img.save("images/maps/"+map_base+".png", "PNG")
                ###remove .jpg
                os.remove("images/maps/"+map_base+".jpg")

    ###now make the image
    image_text = "TSC Server\n"
    image_text += "Players: " + player_text + "\nCurrent Map: " + map_text

    img = bf1_draw_image("images/maps/"+map_base+".png", image_text, 22)
    img.save("images/TSC_server.png", "PNG")


#####MAIN

###Discord setup
#https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-the-developer-portal
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

client = discord.Client()

bot = commands.Bot(command_prefix='!')

@bot.command(name='bf1basicstats', help = "gives basic Battlefield 1 stats")
async def bf1_basic_stats(ctx, username):
    web_data = read_bf1tracker_stats(username)
    if len([tag for tag in web_data.find_all("div") if tag.attrs.get("class", "crap") == ["stats-large"]]) == 0:
        await ctx.channel.send(username+" does not exist!")
    else:
        rank = web_data.find_all("div")[34].find_all("span")[0].text.split(" ")[-1]
        image = get_general_stats(username, int(rank), [tag for tag in web_data.find_all("div") if tag.attrs.get("class", "crap") == ["stat"]])
        #https://stackoverflow.com/questions/50860397/discord-py-bot-sending-file-to-discord-channel
        await ctx.channel.send("Battlefield 1 Stats for "+username+" :", file = discord.File(image))

@bot.command(name='bf1top10weapons', help = "shows a chart of top 10 weapons by kills")
async def bf1_top_10_weapons(ctx, username):
    web_data = read_bf1tracker_stats(username)
    if len([tag for tag in web_data.find_all("div") if tag.attrs.get("class", "crap") == ["stats-large"]]) == 0:
        await ctx.channel.send(username+" does not exist!")
    else:
        image = top_10_weapons(username, False)
        await ctx.channel.send("BF1 Top 10 Weapons by Kills for "+username+" :", file = discord.File(image))

@bot.command(name='bf1top10all', help = "shows a chart of top 10 weapons/vehicles by kills")
async def bf1_top_10_all(ctx, username):
    web_data = read_bf1tracker_stats(username)
    if len([tag for tag in web_data.find_all("div") if tag.attrs.get("class", "crap") == ["stats-large"]]) == 0:
        await ctx.channel.send(username+" does not exist!")
    else:
        image = top_10_weapons(username, True)
        await ctx.channel.send("BF1 Top 10 by Kills for "+username+" :", file = discord.File(image))

@bot.command(name='bf1TSCserverstats', help = "shows current players and map of BF1 TSC server")
async def bf1_TSC_server_stats(ctx):
    try:
        tsc_server_data()
    except:
        await ctx.channel.send("BF1Tracker server page is currently down.")
    else:
        await ctx.channel.send("Our beautiful BF1 Server:", file = discord.File("images/TSC_server.png"))


bot.run(token)



###General stats
#get_general_stats(username, int(rank), web_chunks["General stats"], web_chunks["Combat stats"], web_chunks["Rankings"])

###Weapons
#top_10_weapons(web_chunks["Weapons"])

