"""
duel.py - clone of a mIRC script to let users duel each other
Copyright 2015 dgw
"""

from __future__ import division
from sopel import module, tools
import random
import time

TIMEOUT = 600


@module.commands('duel')
@module.require_chanmsg
def duel_cmd(bot, trigger):
    return duel(bot, trigger.sender, trigger.nick, trigger.group(3) or '', is_admin=trigger.admin)


def duel(bot, channel, instigator, target, is_admin=False):
    target = tools.Identifier(target or '')
    if not target:
        bot.reply("Who did you want to duel?")
        return module.NOLIMIT
    if get_unduelable(bot, instigator):
        bot.say("Try again when you're duelable, %s." % instigator)
        return module.NOLIMIT
    if target == bot.nick:
        bot.say("I refuse to duel with the yeller-bellied likes of you!")
        return module.NOLIMIT
    if is_self(bot, instigator, target):
        if not get_self_duels(bot, channel):
            bot.say("You can't duel yourself, you coward!")
            return module.NOLIMIT
    if target.lower() not in bot.privileges[channel.lower()]:
        bot.say("You can't duel people who don't exist!")
        return module.NOLIMIT
    target_unduelable = get_unduelable(bot, target)
    if target_unduelable and not is_admin:
        bot.say("You SHALL NOT duel %s!" % target)
        return module.NOLIMIT
    time_since = time_since_duel(bot, channel, instigator)
    if time_since < TIMEOUT:
        bot.notice("Next duel will be available in %d seconds." % (TIMEOUT - time_since), instigator)
        return module.NOLIMIT
    if is_admin and target_unduelable:
        bot.notice("Just so you know, %s is marked as unduelable." % target, instigator)
    kicking = kicking_available(bot, channel)
    msg = "%s vs. %s, " % (instigator, target)
    msg += "loser gets kicked!" if kicking else "loser's a yeller belly!"
    bot.say(msg)
    combatants = sorted([instigator, target])
    random.shuffle(combatants)
    winner = combatants.pop()
    loser = combatants.pop()
    bot.say("%s wins!" % winner)
    if loser == target:
        kmsg = "%s done killed ya!" % instigator
    else:
        kmsg = "You done got yerself killed!"
    if kicking and not target_unduelable:
        bot.write(['KICK', channel, loser], kmsg)
    else:
        bot.say(kmsg[:-1] + ", " + loser + kmsg[-1:])
    now = time.time()
    bot.db.set_nick_value(instigator, 'duel_last', now)
    bot.db.set_channel_value(channel, 'duel_last', now)
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


@module.commands('dueloff')
@module.example(".dueloff")
def exclude(bot, trigger):
    """
    Disable other users' ability to duel you (admins: or another user)
    """
    if not trigger.group(3):
        target = trigger.nick
        time_since = time_since_duel(bot, trigger.sender, target)
        if time_since < TIMEOUT:
            bot.notice("You must wait %.0f seconds before disabling duels, because you recently initiated a duel."
                       % (TIMEOUT - time_since), target)
            return
    else:
        target = tools.Identifier(trigger.group(3))
    if not trigger.admin and target != trigger.nick:
        bot.say("Only bot admins can mark other users as unduelable.")
        return
    set_unduelable(bot, target, True)
    bot.say("Disabled duels for %s." % target)


@module.commands('duelon')
@module.example(".duelon")
def unexclude(bot, trigger):
    """
    Re-enable other users' ability to duel you (admins: or another user)
    """
    if not trigger.group(3):
        target = trigger.nick
    else:
        target = tools.Identifier(trigger.group(3))
    if not trigger.admin and target != trigger.nick:
        bot.say("Only bot admins can mark other users as duelable.")
        return
    set_unduelable(bot, target, False)
    bot.say("Enabled duels for %s." % target)


@module.commands('duelself', 'duelcw', 'duelkick', 'duelkicks')
@module.require_chanmsg
def duel_setting(bot, trigger):
    cmd = trigger.group(1) or None
    arg = trigger.group(3) or None
    if cmd == 'duelself':
        setting = 'self-duel'
    elif cmd == 'duelcw':
        setting = 'channel-wide duel'
    elif cmd == 'duelkick' or cmd == 'duelkicks':
        setting = 'duel kick'
    else:
        bot.reply("Unknown setting command %s, exiting. Please report this to %s." % (cmd, bot.config.core.owner))
        return module.NOLIMIT
    if not arg:  # return current setting
        if cmd == 'duelself':
            enable = get_self_duels(bot, trigger.sender)
        elif cmd == 'duelcw':
            enable = get_duel_chanwide(bot, trigger.sender)
        elif cmd == 'duelkick' or cmd == 'duelkicks':
            enable = get_duel_kicks(bot, trigger.sender)
        else:  # this is already caught above, but this else keeps PyCharm happy
            bot.reply("Unknown setting command %s, exiting. Please report this to %s." % (cmd, bot.config.core.owner))
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
    elif cmd == 'duelkick' or cmd == 'duelkicks':
        set_duel_kicks(bot, trigger.sender, enable)
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


def get_unduelable(bot, nick):
    return bot.db.get_nick_value(nick, 'unduelable') or False


def get_self_duels(bot, channel):
    return bot.db.get_channel_value(channel, 'enable_duel_self') or False


def get_duel_chanwide(bot, channel):
    return bot.db.get_channel_value(channel, 'duel_chanwide') or False


def get_duel_kicks(bot, channel):
    kicks = bot.db.get_channel_value(channel, 'duel_kicks')
    return True if kicks is None else kicks


def time_since_duel(bot, channel, nick):
    now = time.time()
    if get_duel_chanwide(bot, channel):
        last = bot.db.get_channel_value(channel, 'duel_last') or 0
    else:
        last = bot.db.get_nick_value(nick, 'duel_last') or 0
    return abs(now - last)


def update_duels(bot, nick, won=False):
    wins, losses = get_duels(bot, nick)
    if won:
        bot.db.set_nick_value(nick, 'duel_wins', wins + 1)
    else:
        bot.db.set_nick_value(nick, 'duel_losses', losses + 1)


def set_unduelable(bot, nick, status=False):
    bot.db.set_nick_value(nick, 'unduelable', status)


def set_self_duels(bot, channel, status=True):
    bot.db.set_channel_value(channel, 'enable_duel_self', status)


def set_duel_chanwide(bot, channel, status=False):
    bot.db.set_channel_value(channel, 'duel_chanwide', status)


def set_duel_kicks(bot, channel, status=True):
    bot.db.set_channel_value(channel, 'duel_kicks', status)


def duel_finished(bot, winner, loser):
    update_duels(bot, winner, True)
    update_duels(bot, loser, False)


def kicking_available(bot, channel):
    return get_duel_kicks(bot, channel) and bot.privileges[channel.lower()][bot.nick.lower()] >= module.OP
