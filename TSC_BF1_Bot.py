import requests, bs4, sys, re, plotly, os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands
from dotenv import load_dotenv
plotly.io.orca.config.executable = r"C:\Users\Alexander\AppData\Local\Programs\orca\orca.exe"

#####GLOBAL
bf1_classes = ["Tanker/Pilot", "Assault", "Medic", "Support", "Scout", "Elite", "All"]

smgs = ["MP 18", "Automatico M1918", "Hellriegel 1915", "Annihilator", "M1919 SMG", "Ribeyrolles 1918", "SMG 08/18", "M1917 Trench Carbine", "Maschinenpistole M1912/P.16", "RSC SMG"]
shotguns = ["M97 Trench Gun", "Model 10-A", "12g Automatic", "Sjögren Inertial", "Model 1900"]
sl_rifles = ["Cei-Rigotti", "Selbstlader M1916", "M1907 SL", "Mondragón", "Autoloading 8", "Selbstlader 1906", "Fedorov-Degtyarev", "RSC 1917", "Fedorov Avtomat", "General Liu Rifle", "Farquhar-Hill", "Howell Automatic"]
lmgs = ["Lewis Gun", "M1909 Benét-Mercié", "Madsen MG", "MG15 n.A.", "BAR M1918", "Huot Automatic", "BAR M1918A2", "Burton LMR", "Chauchat", "Parabellum MG14/17", "Perino Model 1908", "M1917 MG", "lMG 08/18"]
sa_rifles = ["SMLE MKIII", "Gewehr 98", "Russian 1895", "Gewehr M.95", "M1903", "Martini-Henry", "Mosin-Nagant M38 Carbine", "Lebel Model 1886", "Mosin-Nagant M91", "Vetterli-Vitali M1870/87", "Carcano M91 Carbine", "Type 38 Arisaka",
            "Ross MkIII", "M1917 Enfield"]
carbine_pistols = ["C96 Carbine", "Frommer Stop Auto", "M1911 Extended", "Pieper M1893", "P08 Artillerie", "Mle 1903 Extended", "C93 Carbine", "Sawed Off Shotgun"]
pistols_all = ["M1911", "P08 Pistol", "Mle 1903", "No. 3 Revolver", "C93", "Kolibri", "M1911A1", "Peacekeeper", "Nagant Revolver", "Obrez Pistol", "Revolver Mk VI"]
pistols_assault = ["Gasser M1870", "1903 Hammerless", "Howdah Pistol"]
pistols_medic = ["Auto Revolver", "Taschenpistole M1914", "C96"]
pistols_support = ["Bull Dog Revolver", "Modello 1915", "Repetierpistole M1912"]
pistols_scout = ["Bodeo 1889", "Frommer Stop", "Mars Automatic"]
elite_weapons = ["Wex", "MG 08/15", "Villar Perosa", "Tankgewehr M1918", "Martini-Henry Grenade Launcher"]

gear_assault = ["Anti-Tank Grenade", "AT Mine", "AT Rocket Gun", "Dynamite", "AA Rocket Gun"]
gear_medic = ["Rifle Grenade"]
gear_support = ["Limpet Charge", "Mortar", "Repair Tool", "Crossbow Launcher"]
gear_scout = ["K Bullet", "Flare Gun", "Tripwire Bomb"]

weapons_by_class = {"Assault":smgs + shotguns + pistols_assault + gear_assault,
                    "Medic":sl_rifles + pistols_medic + gear_medic,
                    "Support":lmgs + pistols_support + gear_support,
                    "Scout":sa_rifles + pistols_scout + gear_scout,
                    "Tanker/Pilot":carbine_pistols,
                    "Elite":elite_weapons,
                    "All":pistols_all}

rec_x = 500
rec_y = 500



#####FUNCTIONS
def read_bf1stats(username):
    r = requests.get("http://bf1stats.com/pc/" + username)
    web_data = bs4.BeautifulSoup(r.text, "html.parser")
    return web_data, {item.header.get_text():item for item in web_data.findAll("article") if item.header is not None}


def process_bf1stats_line(out_dict, line, attributes):
    """processes line from bf1stats"""
    if len(line.attrs.keys()) > 0:
        for new_key, identifier in attributes:
            if identifier in list(line.attrs.values())[0]:
                #am I a special case?
                if identifier in [".kdr"]:
                    out_dict[new_key] = line.find("span").text
                else:
                    out_dict[new_key] = line.contents[0].replace(",", "")
                #am I zero?
                if out_dict[new_key] == "-":
                    out_dict[new_key] = 0
                #am I a percent?
                elif "%" in out_dict[new_key]:
                    out_dict[new_key] = float(out_dict[new_key][:-1])
                #am I a decimal?
                elif "." in out_dict[new_key] and out_dict[new_key].replace(".", "").isdigit():
                    out_dict[new_key] = float(out_dict[new_key])
                else:
                    out_dict[new_key] = int(out_dict[new_key])
                break
    return out_dict

def process_stats_generic(data, attributes):
    """parses information for most stats"""
    out_dict = {}
    for row in data.find("table").find_all("tr"):
        for td_piece in row.find_all("td"):
            #print(td_piece.attrs)
            out_dict = process_bf1stats_line(out_dict, td_piece, attributes)
    return out_dict

def process_weapon(wep_row):
    """parse data for weapons from bf1stats"""
    out_dict = {}
    for td_piece in wep_row.find_all("td"):
        if "class" in td_piece.attrs and td_piece.attrs["class"][0] == "left":
            out_dict["name"] = str(td_piece.contents[0])
        else:
            #print(td_piece.attrs.values())
            out_dict = process_bf1stats_line(out_dict, td_piece, [["kills", ".kills"], ["headshots", ".headshots"], ["shots", ".shots"], ["hits", ".hits"]])
            ###class information
            for bf1_class in bf1_classes:
                if any(out_dict["name"].startswith(wep) for wep in weapons_by_class[bf1_class]):
                    out_dict["class"] = bf1_class
                    break
            if "class" not in out_dict.keys():
                out_dict["class"] = "All"
    return out_dict

def get_general_stats(username, rank, general_data, combat_data, rankings_data):
    """pulls basic overview stats from bf1stats"""

    ###create big dictionary with all info
    user_info = {"Rank": rank}
    #https://www.geeksforgeeks.org/python-merging-two-dictionaries/
    user_info.update(process_stats_generic(general_data, [["Rounds",".numRounds"],["Wins", ".numWins"],["Losses", ".numLosses"]]))
    user_info.update(process_stats_generic(combat_data, [["Kills", ".kills"], ["Deaths", ".deaths"], ["KDR", ".kdr"], ["Headshots", ".headshots"], ["Accuracy", ".accuracy"]]))
    user_info.update(process_stats_generic(rankings_data, [["SPM",".extra.spm"], ["KPM", ".extra.kpm"]]))
    #print(user_info)

    ###Initialize image magic
    #https://haptik.ai/tech/putting-text-on-image-using-python/
    image = Image.open(r'C:\Users\Alexander\Pictures\ww1_test.png')
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
    font = ImageFont.truetype(r'C:\Users\Alexander\Desktop\fonts\TravelingTypewriter.ttf', size=30)
    image_text = username + "\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Rank", "SPM", "KPM"]]) + "\n\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Rounds", "Wins", "Losses"]]) + "\n\n"
    image_text += "\n".join([cat+": "+str(user_info[cat]) for cat in ["Kills", "Deaths", "KDR", "Headshots", "Accuracy"]])

    #https://stackoverflow.com/questions/1970807/center-middle-align-text-with-pil
    w, h = draw.textsize(image_text, font = font)
    draw.text(((image_x-w)/2,(image_y-h)/2), image_text, fill="white", font=font, align = "center")
    image.save("basic_stats_"+username+".png", "PNG")
    return "basic_stats_"+username+".png"
    #image.show()
    #draw.text((100,100))
    

    #image.show()


def top_10_weapons(username, weapons_data):
    """graphs user's top 10 weapons"""
    weapons = []
    for row in weapons_data.find("div").find("table").find_all("tr")[1:]:
        weapons.append(process_weapon(row))
        
    weapons_frame = pd.DataFrame(weapons)

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
    fig.update_layout(title_text=username + ' : Top 10 Weapons by Kills',
                        showlegend = True,
                        xaxis = {
                            'categoryorder': 'array',
                            'categoryarray': list(weapons_top_10["name"])
                        }
    )
    #print(fig)
    #fig.show()
    fig.write_image("top_10_weapons_"+username+".png")
    return "top_10_weapons_"+username+".png"




#####MAIN
#web_data, web_chunks = read_bf1stats("MogenarZ")
#image = top_10_weapons("MogenarZ", web_chunks["Weapons"])
#sys.exit()

###Discord setup
#https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-the-developer-portal
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

client = discord.Client()

bot = commands.Bot(command_prefix='!')

@bot.command(name='bf1basicstats', help = "gives basic Battlefield 1 stats")
async def bf1_basic_stats(ctx, username):
    web_data, web_chunks = read_bf1stats(username)
    rank = web_data.findAll("article")[0].find("div").findAll("div")[1].text.split(" ")[0]
    image = get_general_stats(username, int(rank), web_chunks["General stats"], web_chunks["Combat stats"], web_chunks["Rankings"])
    #https://stackoverflow.com/questions/50860397/discord-py-bot-sending-file-to-discord-channel
    await ctx.channel.send("Battlefield 1 Stats for "+username+" :", file = discord.File(image))

@bot.command(name='bf1top10weapons', help = "shows a chart of top 10 weapons by kills")
async def bf1_basic_stats(ctx, username):
    web_data, web_chunks = read_bf1stats(username)
    image = top_10_weapons(username, web_chunks["Weapons"])
    await ctx.channel.send("BF1 Top 10 Weapons by Kills for "+username+" :", file = discord.File(image))


bot.run(token)



###General stats
#get_general_stats(username, int(rank), web_chunks["General stats"], web_chunks["Combat stats"], web_chunks["Rankings"])

###Weapons
#top_10_weapons(web_chunks["Weapons"])

