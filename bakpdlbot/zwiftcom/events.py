import re
import logging
from abc import ABC

import pendulum
import requests

from .const import worlds, routes
from ..simple import get_userlist

logger = logging.getLogger(__name__)

def format_timestamp(v):
    return pendulum.parse(v)


class Eventish(ABC):
    RACE = 'RACE'
    RIDE = 'GROUP_RIDE'
    GROUP_WORKOUT = 'GROUP_WORKOUT'
    TIME_TRIAL = 'TIME_TRIAL'

    CYCLING = 'CYCLING'
    RUNNING = 'RUNNING'

    # rules
    NO_DRAFTING = 'NO_DRAFTING'
    NO_POWERUPS = 'NO_POWERUPS'
    LADIES_ONLY = 'LADIES_ONLY'
    ALLOWS_LATE_JOIN = 'ALLOWS_LATE_JOIN'
    NO_TT_BIKES = 'NO_TT_BIKES'
    SHOW_RACE_RESULTS = 'SHOW_RACE_RESULTS'
    NO_ZPOWER = "ENFORCE_NO_ZPOWER"

    formatters = {}

    @property
    def map(self):
        return self.route['map']

    @property
    def route(self):
        route = routes.get(self.route_id)
        if route is None:
            logger.warning("Unknown route id: %s", self.route_id)
            route = 'Unknown'
        return route

    @property
    def powerups(self):
        pus = {
            0: 'Feather',
            1: 'Draft',
            # 2: '2',
            3: 'Large XP',
            4: 'Burrito',
            5: 'Aero',
            6: 'Ghost',
            7: 'Steamroller',
            8: 'Anvil',
        }
        for tag in self.tags:
            if tag.startswith('powerup_percent='):
                try:
                    m = re.match('^powerup_percent=[^0-9,]?,?(?P<pcts>[0-9,]+?),?[^0-9,]?$', tag)
                    pct_list = list(map(int, m.group('pcts').split(',')))
                    pcts = dict(zip(map(lambda x: pus.get(x, "Unknown ({})".format(x)), pct_list[::2]), pct_list[1::2]))
                    return pcts
                except:
                    # print("Couldn't parse {} - {}".format(self.name, tag))
                    return None
        return None

    @property
    def trainer_difficulty_min(self):
        for tag in self.tags:
            if tag.startswith('trainer_difficulty_min='):
                return tag.split('trainer_difficulty_min=')[-1]
        return None

    def __init__(self, data: dict):
        self._data = data
        self._signups = None

    def __getattr__(self, item):
        cc_item = ''.join(word.title() for word in item.split('_'))
        cc_item = cc_item[0].lower() + cc_item[1:]
        value = self._data[cc_item]
        f = self.formatters.get(item, lambda x: x)
        return f(value)


class EventSubgroup(Eventish):
    formatters = {
        "registration_start": format_timestamp,
        "registration_end": format_timestamp,
        "line_up_start": format_timestamp,
        "line_up_end": format_timestamp,
        "event_subgroup_start": format_timestamp,
    }


class Event(Eventish):
    formatters = {
        "event_start": format_timestamp,
        "event_subgroups": lambda sgs: [EventSubgroup(sg) for sg in sgs],
    }

    @property
    def url(self) -> str:
        return "https://www.zwift.com/events/view/{}".format(self.id)

    def get_signups(self, scraper):
        race = scraper.race(self.id)
        check_signups = get_userlist()['zwiftid'].tolist()
        self._signups = [rider for rider in race.signups if
                         (rider.teamid is not None and rider.teamid == '13264') or
                         (rider.id in check_signups)]


def get_event(eid: int, secret: str = None) -> Event:
    url = "https://us-or-rly101.zwift.com/api/public/events/{}".format(int(eid))
    if secret is not None:
        params = {'eventSecret': secret}
    else:
        params = {}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return Event(resp.json())
