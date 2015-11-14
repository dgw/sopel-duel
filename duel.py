"""
duel.py - clone of a mIRC script to let users duel each other
Copyright 2015 dgw
"""

from __future__ import division
from willie import module, tools
import random
import time

TIMEOUT = 600


@module.commands('duel')
@module.require_chanmsg
def duel(bot, trigger):
    time_since = time_since_duel(bot, trigger.nick)
    if time_since < TIMEOUT:
        bot.notice("You must wait %d seconds until your next duel." % (TIMEOUT - time_since), trigger.nick)
        return module.NOLIMIT
    target = tools.Identifier(trigger.group(3) or '')
    if not target:
        bot.reply("Who did you want to duel?")
        return module.NOLIMIT
    if target == bot.nick:
        bot.say("I refuse to duel with the yeller-bellied likes of you!")
        return module.NOLIMIT
    if target == trigger.nick:
        if get_self_duels(bot, trigger.sender):
            bot.say("You can't duel yourself, you coward!")
            return module.NOLIMIT
    if target.lower() not in bot.privileges[trigger.sender.lower()]:
        bot.say("You can't duel people who don't exist!")
        return module.NOLIMIT
    bot.say("%s vs. %s, loser gets kicked!" % (trigger.nick, target))
    combatants = [trigger.nick, target]
    random.shuffle(combatants)
    winner = combatants.pop()
    loser = combatants.pop()
    bot.say("%s wins!" % winner)
    if bot.privileges[trigger.sender.lower()][bot.nick.lower()] >= module.OP:
        if loser == target:
            msg = "%s done killed ya!" % trigger.nick
        else:
            msg = "You done got yerself killed!"
        bot.write(['KICK', trigger.sender, loser], msg)
    bot.db.set_nick_value(trigger.nick, 'duel_last', time.time())
    duel_finished(bot, winner, loser)


@module.commands('duels')
def duels(bot, trigger):
    target = trigger.group(3) or trigger.nick
    wins, losses = get_duels(bot, target)
    total = wins + losses
    if not total:
        bot.say("%s has no duel record!" % target)
        return module.NOLIMIT
    win_rate = wins / total * 100
    bot.say("%s has won %d out of %d duels (%.2f%%)." % (target, wins, total, win_rate))


@module.commands('duelself')
@module.require_chanmsg
def duel_self(bot, trigger, enable=None):
    arg = trigger.group(3) or None
    if not arg:  # return current setting
        enable = get_self_duels(bot, trigger.sender)
        bot.say("Self-duels are %s in %s." % ("enabled" if enable else "disabled", trigger.sender))
        return module.NOLIMIT
    if not trigger.admin and bot.privileges[trigger.sender.lower()][trigger.nick.lower()] < module.ADMIN:
        bot.reply("Only channel admins can change this setting.")
        return
    if enable is None:  # Called directly, so parse expected argument
        if trigger.group(3).lower() == 'on':
            enable = True
        elif trigger.group(3).lower() == 'off':
            enable = False
        else:
            bot.reply("Invalid self-duel setting. Valid values: 'on', 'off'.")
            return module.NOLIMIT
    if enable:
        pfx = 'en'
    else:
        pfx = 'dis'
    set_self_duels(bot, trigger.sender, enable)
    bot.say("Self-duels are now %sabled in %s." % (pfx, trigger.sender))


@module.commands('duelselfon')
@module.require_chanmsg
def duel_self_yes(bot, trigger):
    duel_self(bot, trigger, True)


@module.commands('duelselfoff')
@module.require_chanmsg
def duel_self_no(bot, trigger):
    duel_self(bot, trigger, False)


def get_duels(bot, nick):
    wins = bot.db.get_nick_value(nick, 'duel_wins') or 0
    losses = bot.db.get_nick_value(nick, 'duel_losses') or 0
    return wins, losses


def get_self_duels(bot, channel):
    return bot.db.get_channel_value(channel, 'enable_duel_self') or False


def time_since_duel(bot, nick):
    now = time.time()
    last = bot.db.get_nick_value(nick, 'duel_last') or 0
    return abs(now - last)


def update_duels(bot, nick, won=False):
    wins, losses = get_duels(bot, nick)
    if won:
        bot.db.set_nick_value(nick, 'duel_wins', wins + 1)
    else:
        bot.db.set_nick_value(nick, 'duel_losses', losses + 1)


def set_self_duels(bot, channel, status=True):
    bot.db.set_channel_value(channel, 'enable_duel_self', status)


def duel_finished(bot, winner, loser):
    update_duels(bot, winner, True)
    update_duels(bot, loser, False)
