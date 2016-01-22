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
    target = tools.Identifier(trigger.group(3) or '')
    if not target:
        bot.reply("Who did you want to duel?")
        return module.NOLIMIT
    if target == bot.nick:
        bot.say("I refuse to duel with the yeller-bellied likes of you!")
        return module.NOLIMIT
    if is_self(bot, trigger.nick, target):
        if not get_self_duels(bot, trigger.sender):
            bot.say("You can't duel yourself, you coward!")
            return module.NOLIMIT
    if target.lower() not in bot.privileges[trigger.sender.lower()]:
        bot.say("You can't duel people who don't exist!")
        return module.NOLIMIT
    time_since = time_since_duel(bot, trigger)
    if time_since < TIMEOUT:
        bot.notice("Next duel will be available in %d seconds." % (TIMEOUT - time_since), trigger.nick)
        return module.NOLIMIT
    kicking = kicking_available(bot, trigger)
    msg = "%s vs. %s" % (trigger.nick, target)
    msg += ", loser gets kicked!" if kicking else ", loser's a yeller belly!"
    bot.say(msg)
    combatants = sorted([trigger.nick, target])
    random.shuffle(combatants)
    winner = combatants.pop()
    loser = combatants.pop()
    bot.say("%s wins!" % winner)
    if loser == target:
        kmsg = "%s done killed ya!" % trigger.nick
    else:
        kmsg = "You done got yerself killed!"
    if kicking:
        bot.write(['KICK', trigger.sender, loser], kmsg)
    else:
        bot.say(kmsg[:-1] + ", " + loser + kmsg[-1:])
    now = time.time()
    bot.db.set_nick_value(trigger.nick, 'duel_last', now)
    bot.db.set_channel_value(trigger.sender, 'duel_last', now)
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


@module.commands('duelself', 'duelcw')
@module.require_chanmsg
def duel_setting(bot, trigger):
    cmd = trigger.group(1) or None
    arg = trigger.group(3) or None
    if cmd == 'duelself':
        setting = 'self-duel'
    elif cmd == 'duelcw':
        setting = 'channel-wide duel'
    else:
        bot.reply("Unknown setting command %s, exiting. Please report this to my owner." % cmd)
        return module.NOLIMIT
    if not arg:  # return current setting
        if cmd == 'duelself':
            enable = get_self_duels(bot, trigger.sender)
        elif cmd == 'duelcw':
            enable = get_duel_chanwide(bot, trigger.sender)
        else:  # this is already caught above, but this else keeps PyCharm happy
            bot.reply("Unknown setting %s, exiting. Please report this to my owner." % cmd)
            return module.NOLIMIT
        bot.say("%ss are %s in %s." % (setting.capitalize(), "enabled" if enable else "disabled", trigger.sender))
        return module.NOLIMIT
    if not trigger.admin and bot.privileges[trigger.sender.lower()][trigger.nick.lower()] < module.ADMIN:
        bot.reply("Only channel admins can change this setting.")
        return module.NOLIMIT
    # parse expected argument
    arg = arg.lower()
    if arg == 'on':
        enable = True
    elif arg == 'off':
        enable = False
    else:
        bot.reply("Invalid %s setting. Valid values: 'on', 'off'." % setting)
        return module.NOLIMIT
    pfx = 'en' if enable else 'dis'
    if cmd == 'duelself':
        set_self_duels(bot, trigger.sender, enable)
    elif cmd == 'duelcw':
        set_duel_chanwide(bot, trigger.sender, enable)
    bot.say("%ss are now %sabled in %s." % (setting.capitalize(), pfx, trigger.sender))


def get_duels(bot, nick):
    wins = bot.db.get_nick_value(nick, 'duel_wins') or 0
    losses = bot.db.get_nick_value(nick, 'duel_losses') or 0
    return wins, losses


def is_self(bot, nick, target):
    nick = tools.Identifier(nick)
    target = tools.Identifier(target)
    if nick == target:
        return True  # shortcut to catch common goofballs
    try:
        nick_id = bot.db.get_nick_id(nick, False)
        target_id = bot.db.get_nick_id(target, False)
    except ValueError:
        return False  # if either nick doesn't have an ID, they can't be in a group
    return nick_id == target_id


def get_self_duels(bot, channel):
    return bot.db.get_channel_value(channel, 'enable_duel_self') or False


def get_duel_chanwide(bot, channel):
    return bot.db.get_channel_value(channel, 'duel_chanwide') or False


def time_since_duel(bot, trigger):
    now = time.time()
    if get_duel_chanwide(bot, trigger.sender):
        last = bot.db.get_channel_value(trigger.sender, 'duel_last') or 0
    else:
        last = bot.db.get_nick_value(trigger.nick, 'duel_last') or 0
    return abs(now - last)


def update_duels(bot, nick, won=False):
    wins, losses = get_duels(bot, nick)
    if won:
        bot.db.set_nick_value(nick, 'duel_wins', wins + 1)
    else:
        bot.db.set_nick_value(nick, 'duel_losses', losses + 1)


def set_self_duels(bot, channel, status=True):
    bot.db.set_channel_value(channel, 'enable_duel_self', status)


def set_duel_chanwide(bot, channel, status=False):
    bot.db.set_channel_value(channel, 'duel_chanwide', status)


def duel_finished(bot, winner, loser):
    update_duels(bot, winner, True)
    update_duels(bot, loser, False)


def kicking_available(bot, trigger):
    return bot.privileges[trigger.sender.lower()][bot.nick.lower()] >= module.OP
