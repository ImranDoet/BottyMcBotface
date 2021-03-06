import datetime as dt
import traceback

import discord
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setpfp")
    @commands.guild_only()
    async def setpfp(self, ctx: commands.Context):
        """Set the bot's profile picture (admin only)
        """

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 7):
            raise commands.BadArgument(
                "You do not have permission to use this command.")
        if len(ctx.message.attachments) < 1:
            raise commands.BadArgument("Please attach an image to use as the profile picture.")
        
        await self.bot.user.edit(avatar=await ctx.message.attachments[0].read())
        await ctx.message.reply(embed=discord.Embed(color=discord.Color.blurple(), description="Done!"), delete_after=5)
        
    @setpfp.error
    async def info_error(self, ctx, error):
        await ctx.message.delete(delay=5)
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.CommandOnCooldown)
            or isinstance(error, commands.CommandInvokeError)
                or isinstance(error, commands.NoPrivateMessage)):
            await self.bot.send_error(ctx, error)
        else:
            await self.bot.send_error(ctx, "A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Admin(bot))
