import asyncio
import aiohttp
import discord

from datetime import datetime
from redbot.core import Config, commands
from discord.ext import tasks


class Football(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=32999999999999, force_registration=True)
        self.apikey = "565ec012251f932ea400000172f681f898f64c54691ae4eca725f978"
        self.baseurl = "http://api.football-api.com/2.0"
        self.config.register_guild(channel={"channelid": None})
        self.config.register_global(
            ratelimit={
                "lastreset": None,
                "calls_left": 1000,
                "lastevent": None,
                "status": None,
            }
        )
        self.reset.start()
        self.stream.start()

    def cog_unload(self):
        self.reset.cancel()
        self.stream.cancel()

    @tasks.loop(seconds=1)
    async def reset(self):
        async with self.config.ratelimit() as ratelimit:
            if not ratelimit["lastreset"] or round(datetime.now().timestamp() - ratelimit["lastreset"]) >= 3600:
                ratelimit["lastreset"] = datetime.now().timestamp()
                ratelimit["calls_left"] = 1000

    @tasks.loop(seconds=60)
    async def stream(self):
        if await self.is_ratelimited:
            return
        data = await self.config.all_guilds()
        for guild in data:
            if not (channel := self.bot.get_channel(data[guild]["channel"]["channelid"])):
                continue
            if not (matchid := await self.get_last_matchid):
                continue
            if not (lineup := await self.get_lineup(matchid[0]["id"])) or len(lineup["match_info"]) == 0:
                continue
            em = discord.Embed(color=discord.Color.green())

            if lineup["lineup"]["localteam"] != [] and lineup["lineup"]["visitorteam"] != []:
                visitor = ""
                local = ""
                for x in lineup["lineup"]:
                    if x == "localteam":
                        for y in lineup["lineup"][x]:
                            local += f"\n**{y['name']}**"
                    else:
                        for y in lineup["lineup"][x]:
                            visitor += f"\n**{y['name']}**"

                em.description = f"__**Local Team**__\n{local}\n\n\n__**Visitor Team**__\n{visitor}"

            async with self.config.ratelimit() as settings:
                if matchid[0]["status"] and matchid[0]["status"] != settings["status"]:
                    if matchid[0]["status"] not in ["FT", "HT"]:
                        em.description = "Match has started!"
                        em.add_field(name="Local Team", value=matchid[0]["localteam_name"])
                        em.add_field(name="Visitor Team", value=matchid[0]["visitorteam_name"])
                    elif matchid[0]["status"] == "HT":
                        em.description = "Match is in halftime!"
                        em.add_field(name="Local Team", value=matchid[0]["localteam_name"])
                        em.add_field(name="Visitor Team", value=matchid[0]["visitorteam_name"])
                        em.add_field(name="Halftime score", value=matchid[0]["ht_score"])
                    else:
                        em.description = "Match is finished!"
                        em.add_field(name="Local Team", value=matchid[0]["localteam_name"])
                        em.add_field(name="Visitor Team", value=matchid[0]["visitorteam_name"])
                        em.add_field(name="Fulltime score", value=matchid[0]["ft_score"])
                    settings["status"] = matchid[0]["status"]

                if matchid[0]["events"] != [] or matchid[0]["events"][0]["id"] != settings["lastevent"]:
                    settings["lastevent"] = matchid[0]["events"][0]["id"]

                    dictt = {
                        "goal": "\U000026BD GOAL",
                        "subst": "\U0001F343 SUBST",
                        "yellowcard": "\U0001F7E8 Yellow Card",
                        "redcard": "\U0001F7E5 Red Card",
                    }

                    em.description = f"**{[y for z, y in dictt.items() if matchid[0]['events'][0]['type'] in z][0]}**"
                    em.add_field(
                        name="Team",
                        value=matchid[0]["localteam_name"] if matchid[0]["events"][0]["team"] == "localteam" else matchid[0]["visitorteam_name"],
                    )
                    em.add_field(name="Player", value=matchid[0]["events"][0]["player"])
                    if matchid[0]["events"][0]["type"] == "subst":
                        em.add_field(
                            name="Substitute",
                            value=f"{matchid[0]['events'][0]['assist']}\nMinutes: {matchid[0]['events'][0]['minute']}",
                        )
                    elif matchid[0]["events"][0]["type"] == "goal":
                        em.add_field(
                            name="Result",
                            value=f"{matchid[0]['events'][0]['result']}\nMinutes: {matchid[0]['events'][0]['minute']}\nAssist: {matchid[0]['events'][0]['assist']}",
                        )
                    elif matchid[0]["events"][0]["type"] in ["yellowcard", "redcard"]:
                        em.add_field(
                            name="Behavior",
                            value=f"{matchid[0]['events'][0]['assist']}\nMinutes: {matchid[0]['events'][0]['minute']}",
                        )

            await channel.send(embed=em)

    async def get_5last_results(self, from_date: str, current_date: str):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.baseurl}/matches?team_id=9259&from_date={from_date}&to_date={current_date}&Authorization={self.apikey}"
                ) as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @property
    async def get_last_matchid(self):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.baseurl}/matches?team_id=9259&from_date={datetime.now().strftime('%d.%m.%Y')}&to_date={datetime.now().strftime('%d.%m.%Y')}&Authorization={self.apikey}"
                ) as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @property
    async def get_squad(self):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.baseurl}/team/9259?Authorization={self.apikey}") as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @property
    async def get_current_match(self):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.baseurl}/matches?team_id=9259&Authorization={self.apikey}") as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @property
    async def get_pltable(self):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.baseurl}/standings/1204?Authorization={self.apikey}") as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @property
    async def is_ratelimited(self):
        async with self.config.ratelimit() as ratelimit:
            if ratelimit["calls_left"] == 0:
                return True
            return False

    async def get_lineup(self, matchid):
        async with self.config.ratelimit() as ratelimit:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.baseurl}/commentaries/{matchid}?Authorization={self.apikey}") as j:
                    if j.status != 200:
                        ratelimit["calls_left"] -= 1
                        return
                    ratelimit["calls_left"] -= 1
                    return await j.json()

    @commands.command()
    @commands.guild_only()
    async def lineup(self, ctx):
        """Get the lineup for Manchester City."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        if not (matchid := await self.get_last_matchid):
            return await ctx.send("There's no match for now.")

        if not (data := await self.get_lineup(matchid[0]["id"])) or data["match_info"] is None:
            return await ctx.send("Match ID doesn't exist or the lineup has not been announced yet.")

        em = discord.Embed(color=discord.Color.green())
        visitor = ""
        local = ""
        for x in data["lineup"]:
            if x == "localteam":
                for y in data["lineup"][x]:
                    local += f"\n**{y['name']}**"
            else:
                for y in data["lineup"][x]:
                    visitor += f"\n**{y['name']}**"

        em.description = f"__**Local Team**__\n{local}\n\n\n__**Visitor Team**__\n{visitor}"
        try:
            await ctx.author.send(embed=em)
        except:
            await ctx.send(f"{ctx.author.mention}, your dms are closed.")

    @commands.command()
    @commands.is_owner()
    async def setchan(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for the live stream."""
        channel = ctx.channel if not channel else channel
        await self.config.guild(ctx.guild).channel.channelid.set(channel.id)
        await ctx.send(f"`{channel}` has been set to receive stream events.")

    @commands.command()
    @commands.guild_only()
    async def pltable(self, ctx):
        """Get pltable."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        em = discord.Embed(color=discord.Color.green())
        data = await self.get_pltable
        desc = ""

        for x in data:
            desc += (
                f"\n{x['position']}. **{x['team_name']}** | Season: {x['season']} | Country: {x['country']} | Points: {x['points']} | GD: {x['gd']}"
            )

        em.description = desc
        try:
            await ctx.author.send(embed=em)
        except:
            await ctx.send(f"{ctx.author.mention}, your dms are closed.")

    @commands.command()
    @commands.guild_only()
    async def squad(self, ctx):
        """Get Manchester's City squad."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        em = discord.Embed(color=discord.Color.green())
        data = await self.get_squad
        desc = []

        for x in data["squad"]:
            desc.append(
                f"\n○ **{x['name']}** (Nb: {x['number']}) | Pos: {x['position']} | \U0001F489 {x['injured']} | \U0001F3AE {x['minutes']} minutes | \U0001F945 {x['goals']} | \U0001F7E5 {x['redcards']} | \U0001F7E8 {x['yellowcards']}"
            )

        if len(desc) > 10:
            em.description = "".join([x for x in desc][:10])
            try:
                await ctx.author.send(embed=em)
            except:
                await ctx.send(f"{ctx.author.mention}, your dms are closed.")
            em.description = "".join([x for x in desc][10:])
            try:
                await ctx.author.send(embed=em)
            except:
                await ctx.send(f"{ctx.author.mention}, your dms are closed.")

    @commands.command()
    @commands.guild_only()
    async def last5(self, ctx, fromdate: str, todate: str = datetime.now().strftime("%d.%m.%Y")):
        """Get the 5 last results for Manchester FC (Played)."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        data = await self.get_5last_results(fromdate, todate)
        sortedmatch = sorted(
            data,
            key=lambda x: datetime.strptime(x["formatted_date"], "%d.%m.%Y"),
            reverse=False,
        )

        for x in sortedmatch[-5:]:
            em = discord.Embed(
                color=discord.Color.green(),
                title=f"{x['formatted_date']} (id: {x['id']})",
            )
            em.add_field(name=f"Local team (id: {x['localteam_id']})", value=x["localteam_name"])
            em.add_field(
                name=f"Visitor team (id: {x['visitorteam_id']})",
                value=x["visitorteam_name"],
            )
            em.add_field(name="Venue", value=x["venue"])
            em.add_field(name="Local team score", value=x["localteam_score"])
            em.add_field(name="Visitor team score", value=x["visitorteam_score"])
            em.add_field(name="Half-time score", value=x["ht_score"])
            em.add_field(name="Full-time score", value=x["ft_score"])
            if x["et_score"]:
                em.add_field(name="Extended-time score", value=x["et_score"])
            if x["penalty_local"]:
                em.add_field(name="Penalty local", value=x["penalty_local"])
            if x["penalty_visitor"]:
                em.add_field(name="Penalty visitor", value=x["penalty_visitor"])
            try:
                await ctx.author.send(embed=em)
            except:
                await ctx.send(f"{ctx.author.mention}, your dms are closed.")

    @commands.command()
    @commands.guild_only()
    async def stats(self, ctx):
        """Get the score for the current match."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        if not (data := await self.get_current_match):
            return await ctx.send("No match is being played.")

        dictt = {
            "goal": "\U000026BD GOAL",
            "subst": "\U0001F343 SUBST",
            "yellowcard": "\U0001F7E8 Yellow Card",
            "redcard": "\U0001F7E5 Red Card",
        }

        em = discord.Embed(color=discord.Color.orange())
        em.add_field(
            name=f"Local team (id: {data[0]['localteam_id']})",
            value=data[0]["localteam_name"],
        )
        em.add_field(
            name=f"Visitor team (id: {data[0]['visitorteam_id']})",
            value=data[0]["visitorteam_name"],
        )
        em.add_field(name="Venue", value=data[0]["venue"])
        em.add_field(name="Local team score", value=data[0]["localteam_score"])
        em.add_field(name="Visitor team score", value=data[0]["visitorteam_score"])
        em.add_field(
            name="Current game time",
            value=f"{'Finished' if data[0]['timer'] == '' else data[0]['timer'] + ' minutes'}",
        )
        if data[0]["events"] != []:
            desc = ""
            for x in data[0]["events"]:
                desc += f"\n○ **{[y for z, y in dictt.items() if x['type'] in z][0]}** | {'Player: ' + '`'+x['player']+'`' if x['type'] != 'subst' else 'Player: ' + '`'+x['player']+'`' + ' with ' + '`'+x['assist']+'`'} | Team: {data[0]['localteam_name'] if x['team'] == 'localteam' else data[0]['visitorteam_name']}"
            em.description = desc
        try:
            await ctx.author.send(embed=em)
        except:
            await ctx.send(f"{ctx.author.mention}, your dms are closed.")

    @commands.command()
    @commands.guild_only()
    async def time(self, ctx):
        """Get current game time."""
        if await self.is_ratelimited:
            return await ctx.send("You're ratelimited. Please try later.")

        if not (data := await self.get_current_match):
            return await ctx.send("There's no match for now.")

        if data[0]["timer"] == "":
            return await ctx.send("The game might be finished or there's no match for now.")

        em = discord.Embed(color=discord.Color.green())
        em.description = f"Current game time is: `{data[0]['timer']} minutes`."
        await ctx.send(embed=em)
