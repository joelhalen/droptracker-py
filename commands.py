from interactions import Extension, slash_command, SlashContext, Embed
import time
import subprocess
import platform

# Commands for the general user to interact with the bot
class UserCommands(Extension):
    @slash_command(name="help",
                   description="View helpful commands/links for the DropTracker")
    async def help(self, ctx):
        help_embed = Embed(title="", description="", color=0x0ff000)

        help_embed.set_author(name="Help Menu",
                              url="https://www.droptracker.io/docs",
                              icon_url="https://www.droptracker.io/img/droptracker-small.gif")
        help_embed.set_thumbnail(url="https://www.droptracker.io/img/droptracker-small.gif")
        help_embed.set_footer(text="View our documentation to learn more about how to interact with the Discord bot.")

        help_embed.add_field(name="User Commands:",
                             value="" +
                                   "- `/me` - View your account / stats\n" +
                                   "- `/stats` - View general DropTracker statistics, or search for a player/clan.\n" +
                                   "- `/user-config` - Configure your user-specific settings, such as google sheets & webhooks.\n" +
                                   "= `/patreon` - View the benefits of contributing to keeping the DropTracker online via Patreon.", inline=False)
        help_embed.add_field(name="Group Leader Commands:",
                             value="" +
                                   "- `/group` - View relevant config options, member counts, etc." +
                                   "- `/group-config` - Begin configuring the DropTracker bot for use in a Discord server, with a step-by-step walkthrough.\n" +
                                   "- `/members` - View a listing of the top members of your group in real-time.\n" +
                                   "- `/req-refresh` - Request an instant refresh of the database for your group, if something appears missing", inline=False)
        if ctx.guild and ctx.author and ctx.author.roles:
            if "1176291872143052831" in (str(role) for role in ctx.author.roles):
                help_embed.add_field(name="`Administrative Commands`:",
                                     value="" +
                                           "- `/delete-group` - Completely erase a group from the database, including all members and drops" +
                                           "- `/delete-user` - Delete a user from the database, including all drops and correlations.\n" +
                                           "- `/delete-drop` - Remove a drop from the database by providing its ID.\n" +
                                           "- `/user-info` - View information about a user such as their RSNs, discord affiliation, etc.\n" +
                                           "- `/restart` - Force a complete server restart.", inline=False)
        help_embed.add_field(name="Helpful Links",
                             value="[Docs](https://www.droptracker.io/docs) | "+
                             "[Join our Discord](https://www.droptracker.io/discord) | " +
                             "[GitHub](https://www.github.io/joelhalen/droptracker-py) | " + 
                             "[Patreon](https://www.patreon.com/droptracker)", inline=False)
        # Get Discord latency
        int_latency_ms = int(ctx.bot.latency * 1000)

        # Get external latency
        ext_latency_ms = await self.get_external_latency()

        help_embed.add_field(name="Latency",
                             value=f"Discord: `{int_latency_ms} ms`\n" +
                                   f"External: `{ext_latency_ms} ms`", inline=False)

        return await ctx.send(embed=help_embed, ephemeral=True)

    async def get_external_latency(self):
        ## Determine our latency to an external host via a simple ping
        host = "amazon.com"
        ping_command = ["ping", "-c", "1", host]

        try:
            output = subprocess.check_output(ping_command, stderr=subprocess.STDOUT, universal_newlines=True)
            # Extract the time from the output
            if "time=" in output:
                ext_latency_ms = output.split("time=")[-1].split(" ")[0]
                return ext_latency_ms
        except subprocess.CalledProcessError:
            return "N/A"  # If ping fails, return N/A

        return "N/A"
                
        
    @slash_command(name="me",
                   description="View your DropTracker account / stats, or create an account if you don't already have one.")
    async def me_command(self, ctx):
        ## TODO -- check database to see if the user's account exists
        # if user_exists:
        me_embed = Embed(title="Your Account", description="", color=0x0ff000)

        me_embed.set_author(name="Your Account",
                              url=f"https://www.droptracker.io/profile?discordId={str(ctx.user.id)}",
                              icon_url="https://www.droptracker.io/img/droptracker-small.gif")
        me_embed.set_thumbnail(url="https://www.droptracker.io/img/droptracker-small.gif")
        me_embed.set_footer(text="View our documentation to learn more about how to interact with the Discord bot.")
        



# Commands that help configure or change clan-specifics.
class ClanCommands(Extension):
    @slash_command()
    async def group(self, ctx: SlashContext):
        await ctx.send("Hello world!")



# Commands to help moderate the DropTracker as a whole, 
# meant to be used by admins in the droptracker.io discord
class AdminCommands(Extension):
    @slash_command()
    async def test(self, ctx: SlashContext):
        await ctx.send("Hello world!")