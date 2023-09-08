# Discord_Alerts_Cosmos_Proposals

This class monitors the new proposals entering the voting period for Cosmos chains, and sends messages in a Discord channel (configurable) with their details.
It uses the node's API, which needs to be enabled.

It takes into account the different SDK versions as some API endpoints are different between 0.45 and 0.47 for example -- this may need further updates as the Cosmos SDK evolves. 

Usage: <code>python3 proposal_discord_bot.py -n CHAIN_1 IP_1 API_PORT_1 -n CHAIN_2 IP_2 API_PORT_2</code> (no commas between the arguments)

A service file is provided as an example.
