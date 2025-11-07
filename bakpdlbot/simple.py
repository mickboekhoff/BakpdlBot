import pandas
from discord.ext import commands

def get_userlist():
    """Get the userlist"""
    try:
        userlist = pandas.read_csv("user_signups.csv")
    except FileNotFoundError:
        userlist = pandas.DataFrame({"zwiftid": "399078"}, index=[0])
        userlist.to_csv("user_signups.csv", index=False)
    return userlist

def get_eventsecrets():
    """Get event secrets"""
    try:
        eventsecretlist = pandas.read_csv("eventsecrets.csv")
    except FileNotFoundError:
        eventsecretlist = pandas.DataFrame({"eventsecrets": "f375bb9a1257cce25934"}, index=[0])
        eventsecretlist.to_csv("eventsecrets.csv", index=False)
    return eventsecretlist

class SimpleCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sheet', help='Shares the link to the google sheet')
    async def sheet(self, ctx):
        message='Find the google sheet at:\n' \
                '<https://docs.google.com/spreadsheets/d/16ip9cd6kpH2fl0dJYlG4UC1VOJL2eYjd8WSSXJMjss4/edit?usp=sharing>'
        await ctx.send(message)

    @commands.command(name='events', help='Shares the link to backpedal zwift events')
    async def events(self, ctx):
        message='Find our Backpedal events here:\n' \
                '<https://www.zwift.com/events/tag/backpedal>\n' \
                '<https://zwiftpower.com/series.php?id=BACKPEDAL>'
        await ctx.send(message)

    @commands.command(name='add_signups', help='Add zwiftid to follow signups')
    async def add_signups(self, ctx, *args):
        """Add a zwiftid to the userlist"""
        if len(args) > 0:
            userlist = get_userlist()
            userlist = userlist.drop(userlist.index[userlist.zwiftid == args[0]])
            updated_userlist = pandas.concat([userlist, pandas.DataFrame({"zwiftid": args[0]}, index=[0])])
            updated_userlist.to_csv("user_signups.csv", index=False)
            await ctx.send(f"Added {args[0]} to check_signups list")

    @commands.command(name='del_signups', help='Remove zwiftid to not follow signups')
    async def del_signups(self, ctx, *args):
        """Remove a zwiftid from the userlist"""
        if len(args) > 0:
            userlist = get_userlist()
            userlist = userlist.drop(userlist.index[userlist.zwiftid == args[0]])
            userlist.to_csv("user_signups.csv", index=False)
            await ctx.send(f"Removed {args[0]} from check_signups list")

    @commands.command(name='see_signups', help='See zwiftids whose signups are shown')
    async def see_signups(self, ctx):
        """See the userlist"""
        userlist = get_userlist()['zwiftid'].to_list()
        await ctx.send(f"Zwiftids Signup Check: {', '.join([str(zid) for zid in userlist])}")

    @commands.command(name='add_eventsecret', help='Add eventsecret')
    async def add_eventsecret(self, ctx, *args):
        """Add an eventsecret to the eventsecretlist"""
        if len(args) > 0:
            eventsecret = get_eventsecrets()
            eventsecret = eventsecret.drop(eventsecret.index[eventsecret.eventsecrets == args[0]])
            updated_eventsecret = pandas.concat([eventsecret, pandas.DataFrame({"eventsecrets": args[0]}, index=[0])])
            updated_eventsecret.to_csv("eventsecrets.csv", index=False)
            await ctx.send(f"Added {args[0]} to eventsecret list")

    @commands.command(name='del_eventsecret', help='Remove eventsecret')
    async def del_eventsecret(self, ctx, *args):
        """Remove an eventsecret from the eventsecretlist"""
        if len(args) > 0:
            eventsecret = get_eventsecrets()
            eventsecret = eventsecret.drop(eventsecret.index[eventsecret.eventsecrets == args[0]])
            eventsecret.to_csv("eventsecrets.csv", index=False)
            await ctx.send(f"Removed {args[0]} from eventsecret list")

    @commands.command(name='see_eventsecret', help='See eventsecrets')
    async def see_eventsecret(self, ctx):
        """See the eventsecretlist"""
        eventsecret = get_eventsecrets()['eventsecrets'].to_list()
        await ctx.send(f"Event secrets: {', '.join([str(zid) for zid in eventsecret])}")

    # @commands.command(name='best', help='Shares info to Backpedal ESports Tour')
    # async def events(self, ctx):
    #     message = 'Backpedal ESports Tour:\n' \
    #               'Info: <https://docs.google.com/document/d/1LdUMQajmIAd7dB9tTG2VQ6isjfdcepscwnwRX9svezQ/edit?usp=sharing>\n' \
    #               'Standings: <https://docs.google.com/spreadsheets/d/1HF2M5XnX2tPilJrBrLa_jXZgJ8qX3OdJMhQ-QNPbxjY/edit?usp=sharing>\n' \
    #               'Sign-up: <https://forms.gle/EXUBf6hfbZmjerUZA>'
    #     await ctx.send(message)


async def setup(bot):
    await bot.add_cog(SimpleCommands(bot))


async def teardown(bot):
    pass
