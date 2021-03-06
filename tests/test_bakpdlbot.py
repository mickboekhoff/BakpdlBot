#!/usr/bin/env python

"""Tests for `bakpdlbot` package."""


import unittest
from click.testing import CliRunner

from bakpdlbot import bakpdlbot
from bakpdlbot import cli
from discord.ext import commands
from bakpdlbot.googledocs.main import MakeSheetConnection
from bakpdlbot.googledocs.ttt_sheet import FindTttTeam
from bakpdlbot.googledocs.zrl import ZrlSignups, ZrlTeam, GetDiscordNames
from bakpdlbot.zp import ZwiftPower


class TestBakpdlbot(unittest.TestCase):
    """Tests for `bakpdlbot` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_something(self):
        """Test something."""

    def test_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli.main)
        assert result.exit_code == 0
        assert 'bakpdlbot.cli.main' in result.output
        help_result = runner.invoke(cli.main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help  Show this message and exit.' in help_result.output

    def test_ttt(self):
        tname='BAKPDL 1'
        message = FindTttTeam(teamname=tname)
        #message = 'Showing all Backpedal TTT team signups' + '\n'.join([team for team in teams])
        print(message)

    def test_zrlvalues(self):
        values = ZrlSignups()
        print(values)

    def test_zrlteams(self):
        message = ZrlTeam(teamtag='A1', full=False)
        print(message)

    def test_range(self):
        for i in range(1,19):
            print(i)


    def test_google_connection(self):
        service = MakeSheetConnection()

    def test_zwiftid(self):
        # import requests_cache
        # with requests_cache.disabled():
        bot = commands.Bot(command_prefix='$')
        zp = ZwiftPower(bot)
        zwiftid = zp.find_team_member(q='Mick')
        expectedid = 399078
        self.assertEqual(zwiftid[0].id, expectedid, 'Zwift ids not equal')

