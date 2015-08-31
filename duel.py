"""
duel.py - clone of a mIRC script to let users duel each other
Copyright 2015 dgw
"""

from __future__ import division
from willie import module, tools
import random


@module.commands('duel')
@module.require_chanmsg
@module.rate(600)
def duel(bot, trigger):
    target = tools.Identifier(trigger.group(3) or None)
    if not target:
        bot.reply("Who did you want to duel?")
        return module.NOLIMIT
    if target == bot.nick:
        bot.say("I refuse to duel with the yeller-bellied likes of you!")
        return module.NOLIMIT
    bot.say("%s vs. %s, loser gets kicked!" % (trigger.nick, target))
    combatants = [trigger.nick, target]
    random.shuffle(combatants)
    winner = combatants.pop()
    loser = combatants.pop()
    bot.say("%s wins!" % winner)
    if bot.privileges[trigger.sender.lower()][bot.nick.lower()] >= module.OP:
        bot.write(['KICK', trigger.sender, loser], "You done got yerself killed!")
    duel_finished(bot, winner, loser)


@module.commands('duels')
def duels(bot, trigger):
    target = trigger.group(3) or trigger.nick
    wins, losses = get_duels(bot, target)
    total = wins + losses
    win_rate = wins / total * 100
    bot.say("%s has won %d out of %d duels (%.2f%%)." % (target, wins, total, win_rate))


def get_duels(bot, nick):
    wins = bot.db.get_nick_value(nick, 'duel_wins') or 0
    losses = bot.db.get_nick_value(nick, 'duel_losses') or 0
    return wins, losses


def update_duels(bot, nick, won=False):
    wins, losses = get_duels(bot, nick)
    if won:
        bot.db.set_nick_value(nick, 'duel_wins', wins + 1)
    else:
        bot.db.set_nick_value(nick, 'duel_losses', losses + 1)


def duel_finished(bot, winner, loser):
    update_duels(bot, winner, True)
    update_duels(bot, loser, False)
