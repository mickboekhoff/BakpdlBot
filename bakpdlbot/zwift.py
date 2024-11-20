import logging
import re
import asyncio
from datetime import datetime, timedelta

import ago
import discord
from discord import Member, PartialMessageable
from discord.ext import commands, tasks

from . import zwiftcom
from .sheet import Sheet
from .simple import get_userlist
from .zwiftcom import Event
from .zwiftcom.const import items as list_of_items
from .zwiftpower.scraper import get_scraper, Scraper

logger = logging.getLogger(__name__)


class TimeTag:
    def __init__(self, datetime):
        self.datetime = datetime

    def _format(self, type_):
        return "<t:{0:.0f}:{1}>".format(self.datetime.timestamp(), type_)

    @property
    def short_time(self):
        return self._format('t')

    @property
    def long_time(self):
        return self._format('T')

    @property
    def short_date(self):
        return self._format('d')

    @property
    def long_date(self):
        return self._format('D')

    @property
    def long_date_short_time(self):
        return self._format('f')

    @property
    def long_date_short_time_dow(self):
        return self._format('F')

    @property
    def relative(self):
        return self._format('R')

    def __str__(self):
        return "<t:{0:.0f}>".format(self.datetime.timestamp())


async def event_embed(event, emojis=[]):
    """Generate Embed object for a Zwift event"""
    cat_emoji = {}
    for c in 'ABCDE':
        emoji = discord.utils.get(emojis, name='zcat' + c.lower())
        if emoji:
            cat_emoji[c] = emoji

    start = event.event_start
    embed = (
        discord.Embed(title=event.name.replace('|', r'\|'), url=event.url)
            # .set_image(url=event.image_url)
            .add_field(name='Type', value=event.event_type.lower().replace('_', ' ').title())
    )
    embed.description = 'https://zwiftpower.com/events.php?zid={0.id}'.format(event)

    # Check if subgroups are on separate worlds and/or routes
    same_world = len(set([sg.map for sg in event.event_subgroups])) == 1
    same_route = len(set([sg.route['signature'] for sg in event.event_subgroups])) == 1

    if same_route:
        embed.add_field(name='Route', value=event.route['name'])
    if same_world:
        embed.add_field(name='World', value=event.map)

    embed.add_field(name='Start', value=TimeTag(start).long_date_short_time_dow)

    if event.distance_in_meters:
        embed.add_field(name='Custom Distance', value='{:.1f} km'.format(event.distance_in_meters / 1000))
    elif event.duration_in_seconds:
        embed.add_field(name='Duration', value=ago.human(timedelta(seconds=event.duration_in_seconds), past_tense="{}"))
    elif event.laps:
        distance_m = event.route['leadinDistanceInMeters'] + (int(event.laps) * event.route['distanceInMeters'])
        embed.add_field(name='Laps', value="%d (%.1f km)" % (event.laps, distance_m/1000.0))

    cats_text = []
    footer = []
    for subgroup in event.event_subgroups:
        route = "" if same_route else ", {}".format(subgroup.route['name'])
        world = "" if same_world else " ({})".format(subgroup.map)

        cat_rules = ""
        for rule in subgroup.rules_set:
            if rule == Event.NO_DRAFTING:
                cat_rules = '(no draft)'
        for subtag in subgroup.tags:
            if 'trainer_difficulty_min' in subtag and not event.trainer_difficulty_min:
                cat_rules = cat_rules + f'(TD:{float(get_tag_value(subtag, False)):.0%})'
            if 'steering_disabled' in subtag:
                cat_rules = cat_rules + '(no steering)'
        if subgroup.range_access_label:
            access = "{s.range_access_label}".format(s=subgroup)
        else:
            access = "{s.from_pace_value:.1f}-{s.to_pace_value:.1f} w/kg".format(s=subgroup)
        cats_text.append(
            "{emoji} {start} {access}"
            "{route}{world} {cat_rules}".format(
                s=subgroup, emoji=cat_emoji.get(subgroup.subgroup_label, subgroup.subgroup_label,),
                route=route, world=world, cat_rules=cat_rules,
                start=TimeTag(subgroup.event_subgroup_start).short_time,
                access=access
            )
        )
    embed.add_field(name='Cats', value="\n".join(cats_text), inline=False)


    signup_text = []
    for rider in event._signups:
        signup_text.append(
            "{emoji} {ridername}".format(
                emoji=cat_emoji.get(rider.category),
                ridername=rider.name
            )
        )
    if signup_text:
        embed.add_field(name='Signups', value="\n".join(signup_text), inline=False)

    if event.powerups:
        pus = []
        for pu in event.powerups:
            pus.append(f'{pu} - {event.powerups[pu]}%')
        embed.add_field(name='Powerups', value="\n".join(pus), inline=False)

    if event.category_enforcement:
        footer.append('category enforcement')
    if event.trainer_difficulty_min:
        footer.append(f'TD:{float(event.trainer_difficulty_min):.0%}')
    for rule in event.rules_set:
        if rule == Event.NO_DRAFTING:
            footer.append('no draft')
        elif rule == Event.ALLOWS_LATE_JOIN:
            footer.append('late join')
        elif rule == Event.NO_ZPOWER:
            footer.append('no zpower riders')
        elif rule == Event.NO_POWERUPS:
            footer.append('no powerups')
        elif rule == Event.LADIES_ONLY:
            footer.append('ladies only')
        elif rule == Event.NO_TT_BIKES:
            footer.append('no tt bikes')

    if event.bike_hash is not None:
        embed.add_field(name='Fixed Bike', value=get_item(event.bike_hash))

    if event.jersey_hash is not None:
        embed.add_field(name='Fixed jersey', value=get_item(event.jersey_hash))

    for tag in event.tags:
        handle_tag = handle_event_tag(tag)
        if handle_tag is not None:
            footer.append(handle_tag)

    if footer:
        embed.set_footer(text=", ".join(footer))

    return embed

def handle_event_tag(tag):
    """Handle tag from events"""
    if tag == 'doubledraft':
        return 'doubledraft'
    elif tag == 'ttbikesdraft':
        return 'tt bikes draft'
    elif tag == 'jerseyunlock':
        return "jerseyunlock"
    elif 'bike_cda_bias' in tag:
        return f'CDA: {get_tag_value(tag, is_item=False)}'
    elif 'front_wheel_grams' in tag:
        return f'FW grams: {get_tag_value(tag, is_item=False)}'
    elif 'front_wheel_cda_bias' in tag:
        return f'FW CDA: {get_tag_value(tag, is_item=False)}'
    elif 'rear_wheel_grams' in tag:
        return f'RW grams: {get_tag_value(tag, is_item=False)}'
    elif 'rear_wheel_cda_bias' in tag:
        return f'RW CDA: {get_tag_value(tag, is_item=False)}'
    elif 'front_wheel_crr' in tag:
        return f'FW CRR: {get_tag_value(tag, is_item=False)}'
    elif 'fwheel_override' in tag:
        return f'FW override: {get_tag_value(tag)}'
    elif 'rwheeloverride' in tag:
        return f'RW override: {get_tag_value(tag)}'
    elif 'completionprize' in tag:
        return f'Completionprize: {get_tag_value(tag)}'
    return None

def get_tag_value(tag, is_item=True):
    """Obtain value from tag setting"""
    item_id = tag.split('=')[-1]
    if is_item is False:
        return item_id
    try:
        return get_item(int(item_id))
    except:
        return f"Unknown {item_id}"

def get_item(item_id):
    """Obtain item name from item id"""
    if item_id in list_of_items:
        return list_of_items[item_id]['name']
    return f"Unknown ({item_id})"

def get_events_from_user_signups(scraper: Scraper, hours=4):
    """Get all events that known users are signed up for"""
    all_events = {}
    user_list = get_userlist()['zwiftid'].to_list()
    for riderid in user_list:
        riderprofile = scraper.profile(str(riderid))
        signups = riderprofile.signups
        for signup in signups:
            # Filter on events in the next x hours
            if not datetime.timestamp(datetime.now())+(3600*hours)<signup["tm"]:
                all_events[signup["zid"]]=signup["tm"]
    return [eid[0] for eid in sorted(all_events.items(), key=lambda item: item[1])]

async def message_signups_per_event(channel, eid: int, scraper: Scraper, emojis):
    """Send a message per event containing users that have signed up for the event"""
    event = zwiftcom.get_event(eid)
    event.get_signups(scraper)
    embed = await event_embed(event=event, emojis=emojis)
    await channel.send(embed=embed)


class Zwift(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emojis = None
        self.scraper = get_scraper()
        self.scheduled_signup_function.start()
        self.target = None

    @tasks.loop(seconds=1)
    async def scheduled_signup_function(self, c_id=776164827126169600):
        """Scheduled signup function"""

        # Scheduled at 18:00 CET in weekdays, 8:00 CET in weekend
        now = datetime.today()
        hour = 18 if now.weekday() < 5 else 8
        self.target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        diff = (self.target - now).total_seconds()
        if diff < 0:
            next_day = (now + timedelta(days=1))
            hour = 18 if next_day.weekday() < 5 else 8
            self.target = next_day.replace(hour=hour, minute=0, second=0, microsecond=0)
            diff = (self.target - now).total_seconds()
        logger.debug("Scheduling signup check in <%s> seconds", diff)
        await asyncio.sleep(diff)

        self.emojis = await self.bot.get_guild(774255350585098291).fetch_emojis()
        message_channel = (self.bot.get_channel(c_id) or await self.bot.fetch_channel(c_id))
        eventlist = get_events_from_user_signups(self.scraper)
        await message_channel.send("# Backpedal Signups in the upcoming 4 hours: \n"
                             "Want to be added to this list? Type !add_signups yourzwiftid \n"
                             "Want to be removed from this list? Type !del_signups yourzwiftid")
        if not eventlist:
            await message_channel.send("Nobody has signed up to an event! :sweat_smile:")
        for event_id in eventlist:
            await message_signups_per_event(
                channel=message_channel,
                eid=int(event_id),
                scraper=self.scraper,
                emojis=self.emojis)


    @scheduled_signup_function.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener("on_message")
    async def zwift_link_embed(self, message):
        if self.emojis is None:
            self.emojis = await message.guild.fetch_emojis()
        if isinstance(message.channel, PartialMessageable):
            channel = await self.bot.fetch_channel(message.channel.id)
            if channel.name in ('introductions', 'chit-chat', 'gallery', "ed's-little-blog"):
                return
        eventlink = re.compile(
            r'(?:https?:\/\/)(www.)?zwift.com/.*events/.*view/(?P<eid>[0-9]+)(?:\?eventSecret=(?P<secret>[0-9a-z]+))?')
        for m in eventlink.finditer(message.content):
            eid = int(m.group('eid'))
            secret = m.group('secret')
            event = zwiftcom.get_event(eid, secret)
            event.get_signups(self.scraper)
            embed = await event_embed(event, emojis=self.emojis)
            await message.reply(embed=embed)
        if channel.name == "bot-test" and "check-target" in message.content:
            await message.reply(self.target.isoformat())

    @commands.command(name='zwiftid', help='Searches zwiftid of name')
    async def zwift_id(self, ctx, *args):
        zp = ctx.bot.get_cog('ZwiftPower')
        results = {}
        for query, ids in (await self.zwift_id_lookup(ctx, *args)).items():
            if ids is not None and 0 < len(ids) <= 5:
                results[query] = " / ".join(["{p.id} ({p.name})".format(p=zp.scraper.profile(id_)) for id_ in ids])
            else:
                results[query] = "Not found or too many results"
        await ctx.send("\n".join(["{0}: {1}".format(q, r) for q, r in results.items()]))

    async def zwift_id_lookup(self, ctx, *args):
        zp = ctx.bot.get_cog('ZwiftPower')
        sheet: Sheet = ctx.bot.get_cog('Sheet')
        converter = commands.MemberConverter()

        results = {}
        for query in args[:5]:
            logger.info("Looking up zwift id of <%s>", query)

            # First see if it's simply an int
            try:
                results[query] = [int(query)]
                continue
            except ValueError as e:
                pass

            try:
                member: Member = await converter.convert(ctx, query)
                query = member.display_name
                logger.info("Query is a Member - <using %s>", member.display_name)
            except commands.errors.MemberNotFound:
                pass

            # See if we can find a match for the string on the ZP team
            team_member_results = zp.find_team_member(query)
            if len(team_member_results) > 0:
                results[query] = [p.id for p in team_member_results]
                continue

            # See if the input is a Member and look for it int he ZRL sheet
            # It's slow and not very useful. Skip for now
            #try:
            #    member = await converter.convert(ctx, query)
            #    zid = await sheet.discord_to_zwift_id(ctx, member)
            #    if zid:
            #        results[query] = [zid]
            #        continue


            results[query] = None
        return results


async def setup(bot):
    await bot.add_cog(Zwift(bot))


def teardown(bot):
    pass
