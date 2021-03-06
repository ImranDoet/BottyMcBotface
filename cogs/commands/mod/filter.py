import traceback

import discord
from data.filterword import FilterWord
from discord.ext import commands
from discord.ext import menus


class FilterSource(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        permissions = menu.ctx.bot.settings.permissions
        embed = discord.Embed(
            title=f'Filtered words', color=discord.Color.blurple())
        for _, word in entry.items:
            extra = ""
            if word.piracy:
                extra = "\nThis is a piracy word"
            embed.add_field(name=word.word, value=f"Bypassed by: {permissions.level_info(word.bypass)}\nWill report: {word.notify}{extra}")
        embed.set_footer(
            text=f"Page {menu.current_page +1} of {self.get_max_pages()}")
        return embed


class MenuPages(menus.MenuPages):
    async def update(self, payload):
        if self._can_remove_reactions:
            if payload.event_type == 'REACTION_ADD':
                await self.message.remove_reaction(payload.emoji, payload.member)
            elif payload.event_type == 'REACTION_REMOVE':
                return
        await super().update(payload)


class Filters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="offlineping")
    async def offlineping(self, ctx, val: bool):
        """Bot will ping for reports when offline (mod only)

        Example usage:
        --------------
        `!offlineping <true/false>`

        Parameters
        ----------
        val : bool
            True or False, if you want pings or not

        """

        # must be at least a mod
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 5):
            raise commands.BadArgument(
                "You need to be a moderator or higher to use that command.")

        cur = await self.bot.settings.user(ctx.author.id)
        cur.offline_report_ping = val
        cur.save()

        if val:
            await ctx.send("You will now be pinged for reports when offline")
        else:
            await ctx.send("You won't be pinged for reports when offline")

    @commands.guild_only()
    @commands.command(name="filter")
    async def filteradd(self, ctx, notify: bool, bypass: int, *, phrase: str) -> None:
        """Add a word to filter (admin only)

        Example usage:
        -------------
        `!filteradd false 5 :kek:`

        Parameters
        ----------
        notify : bool
            Whether to generate a report or not when this word is filtered
        bypass : int
            Level that can bypass this word
        phrase : str
            Phrase to filter
        """

        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        fw = FilterWord()
        fw.bypass = bypass
        fw.notify = notify
        fw.word = phrase

        await self.bot.settings.add_filtered_word(fw)

        phrase = discord.utils.escape_markdown(phrase)
        phrase = discord.utils.escape_mentions(phrase)

        await ctx.message.reply(f"Added new word to filter! This filter {'will' if notify else 'will not'} ping for reports, level {bypass} can bypass it, and the phrase is {phrase}")

    @commands.guild_only()
    @commands.command(name="filterlist")
    async def filterlist(self, ctx):
        """List filtered words (admin only)

        """

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        filters = self.bot.settings.guild().filter_words
        filters = sorted(filters, key=lambda word: word.word)

        menus = MenuPages(source=FilterSource(
            enumerate(filters), key=lambda t: 1, per_page=12), clear_reactions_after=True)

        await menus.start(ctx)

    @commands.guild_only()
    @commands.command(name="piracy")
    async def piracy(self, ctx, *, word: str):
        """Mark a word as piracy, will be ignored in #dev (admin only)

        Example usage:
        --------------
        `!piracy xd xd xd`

        Parameters
        ----------
        word : str
            Word to mark as piracy

        """
        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        word = word.lower()

        words = self.bot.settings.guild().filter_words
        words = list(filter(lambda w: w.word.lower() == word.lower(), words))
        
        if len(words) > 0:
            await self.bot.settings.remove_filtered_word(words[0].word)
            words[0].piracy = True
            await self.bot.settings.add_filtered_word(words[0])

            await ctx.message.reply("Marked as a piracy word!", delete_after=5)
        else:
            await ctx.message.reply("That word is not filtered.", delete_after=5)            
        await ctx.message.delete(delay=5)

    @commands.guild_only()
    @commands.command(name="filterremove")
    async def filterremove(self, ctx, *, word: str):
        """Remove word from filter (admin only)

        Example usage:
        --------------
        `!filterremove xd xd xd`

        Parameters
        ----------
        word : str
            Word to remove

        """
        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        word = word.lower()

        words = self.bot.settings.guild().filter_words
        words = list(filter(lambda w: w.word.lower() == word.lower(), words))
        
        if len(words) > 0:
            await self.bot.settings.remove_filtered_word(words[0].word)
            await ctx.message.reply("Deleted!", delete_after=5)
        else:
            await ctx.message.reply("That word is not filtered.", delete_after=5)            
        await ctx.message.delete(delay=5)

    @commands.guild_only()
    @commands.command(name="whitelist")
    async def whitelist(self, ctx, id: int):
        """Whitelist a guild from invite filter (admin only)

        Example usage:
        --------------
        `!whitelist 349243932447604736`

        Parameters
        ----------
        id : int
            ID of guild to whitelist

        """

        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        if await self.bot.settings.add_whitelisted_guild(id):
            await ctx.message.reply("Whitelisted.", delete_after=10)
        else:
            await ctx.message.reply("That server is already whitelisted.", delete_after=10)
        await ctx.message.delete(delay=10)

    @commands.guild_only()
    @commands.command(name="ignorechannel")
    async def ignorechannel(self, ctx, channel: discord.TextChannel) -> None:
        """Ignore channel in filter (admin only)

        Example usage:
        -------------
        `!ignorechannel #xd`

        Parameters
        ----------
        channel : discord.Channel
            Channel to ignore

        """

        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        if await self.bot.settings.add_ignored_channel(channel.id):
            await ctx.message.reply("Ignored.", delete_after=10)
        else:
            await ctx.message.reply("That channel is already ignored.", delete_after=10)
        await ctx.message.delete(delay=10)

    @commands.guild_only()
    @commands.command(name="unignorechannel")
    async def unignorechannel(self, ctx, channel: discord.TextChannel) -> None:
        """Unignore channel in filter (admin only)

        Example usage:
        -------------
        `!unignorechannel #xd`

        Parameters
        ----------
        channel : discord.Channel
            Channel to unignore
        """

        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        if await self.bot.settings.remove_ignored_channel(channel.id):
            await ctx.message.reply("Unignored.", delete_after=10)
        else:
            await ctx.message.reply("That channel is not already ignored.", delete_after=10)
        await ctx.message.delete(delay=10)


    @commands.guild_only()
    @commands.command(name="blacklist")
    async def blacklist(self, ctx, id: int):
        """Blacklist a guild from invite filter (admin only)

        Example usage:
        --------------
        `!blacklist 349243932447604736`

        Parameters
        ----------
        id : int
            ID of guild to blacklist

        """

        # must be at least admin
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 6):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be an administator or higher to use that command.")

        if await self.bot.settings.remove_whitelisted_guild(id):
            await ctx.message.reply("Blacklisted.", delete_after=10)
        else:
            await ctx.message.reply("That server is already blacklisted.", delete_after=10)
        await ctx.message.delete(delay=10)

    @piracy.error
    @whitelist.error
    @blacklist.error
    @filterremove.error
    @filteradd.error
    @filterlist.error
    @offlineping.error
    @ignorechannel.error
    @unignorechannel.error
    async def info_error(self, ctx, error):
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await self.bot.send_error(ctx, error)
        else:
            await self.bot.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Filters(bot))
