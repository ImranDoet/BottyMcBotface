import aiohttp
import traceback
from io import BytesIO

import discord
from data.tag import Tag
from discord.ext import commands
from discord.ext import menus


class TagsSource(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        embed = discord.Embed(
            title=f'All tags', color=discord.Color.blurple())
        for tag in entry.items:
            desc = f"Added by: {tag.added_by_tag}\nUsed {tag.use_count} times"
            if tag.image.read() is not None:
                desc += "\nHas image attachment"
            embed.add_field(name=tag.name, value=desc)
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


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="addtag", aliases=['addt'])
    async def addtag(self, ctx, name: str, *, content: str) -> None:
        """Add a tag. Optionally attach an iamge. (Genius only)

        Example usage:
        -------------
        `!addtag roblox This is the content`

        Parameters
        ----------
        name : str
            Name of the tag
        content : str
            Content of the tag
        """

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 4):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be a Genius or higher to use that command.")

        if not name.isalnum():
            await ctx.message.delete()
            raise commands.BadArgument("Tag name must be alphanumeric.")

        if (await self.bot.settings.get_tag(name.lower())) is not None:
            await ctx.message.delete()
            raise commands.BadArgument("Tag with that name already exists.")

        tag = Tag()
        tag.name = name.lower()
        tag.content = content
        tag.added_by_id = ctx.author.id
        tag.added_by_tag = str(ctx.author)
        
        if len(ctx.message.attachments) > 0:
            image, _type = await self.do_content_parsing(ctx.message.attachments[0].url)
            if _type is None:
                raise commands.BadArgument("Attached file was not an image.")
            tag.image.put(image, content_type=_type)

        await self.bot.settings.add_tag(tag)

        await ctx.message.reply(f"Added new tag!", embed=await self.tag_embed(tag), delete_after=10)
        await ctx.message.delete(delay=10)
    
    async def do_content_parsing(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as resp:
                if resp.status != 200:
                    return None, None
                elif resp.headers["CONTENT-TYPE"] not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                    return None, None
                else:
                    async with session.get(url) as resp2:
                        if resp2.status != 200:
                            return None
                        return await resp2.read(), resp2.headers['CONTENT-TYPE']
                        
    async def tag_embed(self, tag):
        embed = discord.Embed(title=tag.name)
        embed.description = tag.content
        embed.timestamp = tag.added_date
        embed.color = discord.Color.blue()

        if tag.image.read() is not None:
            embed.set_image(url="attachment://image.gif" if tag.image.content_type == "image/gif" else "attachment://image.png")
        embed.set_footer(text=f"Added by {tag.added_by_tag} | Used {tag.use_count} times")
        return embed

    @commands.guild_only()
    @commands.command(name="taglist", aliases=['tlist'])
    async def taglist(self, ctx):
        """List all tags
        """

        bot_chan = self.bot.settings.guild().channel_botspam
        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 4) and ctx.channel.id != bot_chan:
            raise commands.BadArgument(
                f"Command only allowed in <#{bot_chan}>")

        tags = sorted(self.bot.settings.guild().tags, key=lambda tag: tag.name)

        if len(tags) == 0:
            raise commands.BadArgument("There are no tags defined.")
        
        menus = MenuPages(source=TagsSource(
            tags, key=lambda t: 1, per_page=12), clear_reactions_after=True)

        await menus.start(ctx)

    @commands.guild_only()
    @commands.command(name="deltag", aliases=['dtag'])
    async def deltag(self, ctx, name: str):
        """Delete tag (geniuses only)

        Example usage:
        --------------
        `!deltag <tagname>`

        Parameters
        ----------
        name : str
            Name of tag to delete

        """

        if not self.bot.settings.permissions.hasAtLeast(ctx.guild, ctx.author, 4):
            await ctx.message.delete()
            raise commands.BadArgument(
                "You need to be a Genius or higher to use that command.")

        name = name.lower()

        tag = await self.bot.settings.get_tag(name)
        if tag is None:
            await ctx.message.delete()
            raise commands.BadArgument("That tag does not exist.")

        await self.bot.settings.remove_tag(name)
        await ctx.message.reply("Deleted.", delete_after=5)
        await ctx.message.delete(delay=5)

    @commands.guild_only()
    @commands.command(name="tag", aliases=['t'])
    async def tag(self, ctx, name: str):
        """Use a tag with a given name.
        
        Example usage
        -------------
        !t roblox

        Parameters
        ----------
        name : str
            Name of tag to use
        """

        name = name.lower()
        tag = await self.bot.settings.get_tag(name)
        
        if tag is None:
            await ctx.message.delete()
            raise commands.BadArgument("That tag does not exist.")
        
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")
        
        await ctx.message.reply(embed=await self.tag_embed(tag), file=file, mention_author=False)

    @tag.error
    @taglist.error
    @deltag.error
    @addtag.error
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
    bot.add_cog(Tags(bot))
