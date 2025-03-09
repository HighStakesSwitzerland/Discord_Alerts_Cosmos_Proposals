from os import path
from time import sleep
from discord import SyncWebhook, Embed
import pytz
from requests import get
from datetime import datetime
from argparse import ArgumentParser

local_directory = path.dirname(path.abspath(__file__))

class QueryProposals:
    """Query the node api and look for new governance proposals in voting period. Only the proposals submitted after the script started running are picked  up."""
    def __init__(self, nodes):
        super().__init__()

        self.nodes = nodes.n #see argument format at the bottom

        self.discord_url = 'https://discord.com/api/webhooks/YOUR_DISCORD_CHANNEL_WEBHOOK_HERE' #depending on the version of the discord package, brackets may be required

        try: #the timestamp is written in a file so that it persists across restarts
            with open(path.join(local_directory, "timestamp"), "r") as f:
                self.now = datetime.strptime(f.read(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.UTC)

        except: #file doesn't exist or data has a wrong format, whatever.
            self.now = datetime.now(tz=pytz.UTC)  # get the current timestamp, to alert only on new proposals.

    def run(self):
        while True:

            pending_proposals = []

            for node in self.nodes:

                base_url = f"http://{node[1]}:{node[2]}"

                #some API endpoints can change depending on the sdk version
                try:
                    sdk_version = int(get(f"{base_url}/cosmos/base/tendermint/v1beta1/node_info", timeout=5).json()['application_version']['cosmos_sdk_version'].split('.')[1])
                #e.g. get should return something like "v0.47.2", so sdk_version = 47. Not a very robust way to do that but endpoints might change before reaching v1.x so this will likely need to be updated.
                except Exception as e:
                    print(f"Can't get node info at {base_url}/cosmos/base/tendermint/v1beta1/node_info.\nPlease check configuration: {str(e)}")
                    exit(1)

                if sdk_version >= 47:
                    proposals_url = '/cosmos/gov/v1/proposals?proposal_status=2'
                else:
                    proposals_url = "/cosmos/gov/v1beta1/proposals?proposal_status=2"

                try:
                    proposals = get(base_url + proposals_url, timeout=10).json()['proposals'] #ignore the pagination. Shouldn't be many, unless spam (e.g. Terra Classic)

                    for i in proposals: #that's clumsy but hey.
                        if datetime.fromisoformat(i['submit_time']) < self.now:

                            proposal_id = i['id'] if sdk_version >= 47 else i['proposal_id']

                            try:
                                proposal_type = self.find_value(i, '@type').split('.')[-1]  # content['@type'].split('.')[-1]
                            except AttributeError:
                                proposal_type = ""
                            if proposal_type == 'MsgSoftwareUpgrade':
                                title = self.find_value(i, 'name')
                                description = self.find_value(i, 'height')
                            else:
                                title = self.find_value(i, 'title')
                                description = self.find_value(i, 'description')
                                if description is None:
                                    description = self.find_value(i, 'summary')

                            if title is None:
                                title = ""
                            if description is None:
                                description = ""

                            voting_end_time = datetime.strftime(datetime.fromisoformat(i['voting_end_time'].split('.')[0]), '%Y-%m-%d %H:%M:%S')

                            proposal = {'validator': node[0], 'number': proposal_id,
                                        'proposal_type': proposal_type,
                                        'title': title,
                                        'description': description, 
                                        'voting_end_time': voting_end_time
                                        }

                            pending_proposals.append(proposal)
                except Exception as e:
                    print(e)

            self.now = datetime.now(tz=pytz.UTC) #reset the timestamp so that at next run, the previous proposals aren't picked up again.
            with open(path.join(local_directory, "timestamp"), "w") as f: #write that in the file
                f.write(str(datetime.now(tz=pytz.UTC)).split('.')[0])

            for proposal in pending_proposals:
                # for i in proposal:
                #     print(i, proposal[i])
                try:
                    title = f"New proposal for {proposal['validator']}"
                    description = f"Type: {proposal['proposal_type']}\nTitle: {proposal['title']}\nDescription: {proposal['description']}"[:(4096 - len(title))]
                    # max length for a discord message is 4096 character. Truncate the description so that it does not exceed that value with the title (it's rare, but happens)

                    webhook = SyncWebhook.from_url(self.discord_url)
                    embed = Embed(title=title, description=description)

                    webhook.send("@everyone", embed=embed) #@everyone can be removed or replaced with another role / member id. If a user, must be like "<@126456789845654>"
                except Exception as e:
                    print(e)
            sleep(3600) #or whatever delay. Not really necessary to have the notification instantly anyway.

    def find_value(self, dictionary, target_key):
        # Check if the target_key exists in the current dictionary
        if target_key in dictionary:
                return dictionary[target_key]
        # If not found, recursively search in nested dictionaries
        for key, value in dictionary.items():
            if isinstance(value, dict):
                result = self.find_value(value, target_key)
                if result is not None:
                    return result
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result = self.find_value(item, target_key)
                        if result is not None:
                            return result

parser = ArgumentParser()
parser.add_argument('-n', action='append', nargs='+', help='Usage: python3 proposals_discord_bot.py -n VALIDATOR1 SERVER_IP1 API_PORT1 -n VALIDATOR2 SERVER_IP2 API_PORT2')
#No commas, no quotes, e.g. : python3 proposal_discord_bot.py -n INJECTIVE 127.23.25.25 1317 -n BAND_PROTOCOL 235.26.35.65 1318
args = parser.parse_args()

if __name__ == '__main__':
    # Note: could be a thread
    QueryProposals(args).run()

