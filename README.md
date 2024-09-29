**![DropTracker](https://www.droptracker.io/img/droptracker-small.gif)
# DropTracker - What is that?

Greetings! Thanks for visiting our GitHub page. The DropTracker is an all-in-one solution for clans and players alike to track their drops received while playing Old School RuneScape. Employing our own custom-built RuneLite plugin, we've been able to provide users with years worth of real-time tracking & statistics.

This repository contains all of the necessary code to operate the Discord bot portion of the app. You can find the other bits here:
[RuneLite Plugin](https://www.github.com/joelhalen/droptracker-plugin)

# Contributing

We are eager for community support to help build the database to be as efficient and low-latency as possible, alongside adding new and interesting features. If you're interested in contributing, you can get started easily by cloning this repository on your local machine & looking through the code.

Check out our [Discord Server](https://www.droptracker.io/discord), where you'll be able to find some up-to-date lists of things that need the most attention currently, along with some suggestions or bug reports you could try to tackle.

## Adding content

The DropTracker is primarily focused around tracking drops and achievements. Any content that aligns with this concept is considered fair game to be included in our system. 
Pull requests that attempt to introduce unexpected or misaligned concepts to the code will be ignored--please try to appease to the masses!

I've attempted to write everything in such a way that it is easily readable for somebody who has somewhat of an understanding of Python.

## Necessary Libraries

You can find a requirements.txt file inside the root directory of the project, which will allow you to install all of the necessary Python packages to run the app. You'll need to create a [Discord App](https://discord.com/developers/applications) (bot), and then generate an API token for it through the Developer portal. 

Alternatively, the important libraries to consider are:

- [interactions (discord-interactions-py) v5.13.2](https://interactions-py.github.io/interactions.py/) - responsible for the Discord bot connection
- [dotenv](https://pypi.org/project/python-dotenv/) - for environmental variables


---

Creating a Discord bot:
https://www.youtube.com/watch?v=GvK-ZigEV4Q

Then you'll need to rename example.env to **.env**. Inside this file, change the necessary variables:

    BOT_TOKEN="your_generated_token_here" # discord bot token
    DB_USER=database_username
    DB_PASS=database_pass
    WOM_API_KEY=optional_wom_key


**
