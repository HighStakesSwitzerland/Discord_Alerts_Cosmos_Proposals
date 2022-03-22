from discord_webhook import DiscordWebhook
from datetime import datetime
from time import sleep
import pytz
import iso8601
from terra_sdk.client.lcd import LCDClient
from terra_sdk.core.gov import ProposalStatus
from argparse import ArgumentParser
from requests import get
from re import findall

class GetNewTerraProposals:
    """A simple class to regularly check for new proposals (in the voting period) for Terra.
    It runs every hour -- update the delay as you like -- and issues a Discord message with the proposal number and the link to Agora"""
    def __init__(self):
        super().__init__()
        self.discord_url = ['https://YOUR_DISCORD_WEBHOOK_ADDRESS_HERE'] #Warning : the brackets must remain.
        self.now = datetime.now(tz=pytz.UTC)  # get the current timestamp, to alert only on new proposals.
        
    def run(self, args):
            
            for i in args:
                if i.lower() == 'terra': #for Terra, we use the public lcd.
                    terra = LCDClient(chain_id="columbus-5", url="https://lcd.terra.dev")

                    try:
                        proposals = terra.gov.proposals({"proposal_status": ProposalStatus(2)}) #status(2) = voting period

                        for i in proposals[0]:
                            if i.submit_time > self.now:  # the proposal entered the voting period after the previous check, so we should alert.
                                link = findall('(https:\/\/agora\S+)', i.content.description)[0]#.split('\n')[0] #the link to the proposal
                                number = i.proposal_id
                                message = f"{i.content.title.upper()}\nProposal {number} is in voting stage!\n{link}"
                                DiscordWebhook(url=self.discord_url, content=message).execute()

                            #now let's update the timestamp so that only later proposals are caught.
                        self.now = datetime.now(tz=pytz.UTC)

                    except Exception as e: #catch any possible exception, be it with the lcd query or the discord message.
                    #it's all very simple so this is just for the initial debugging, not much point setting up a log or anything more sophisticated.
                        print(e)

                else: #if one of the other Cosmos chains, we use the Mintscan api
                    url = f"https://api.mintscan.io/v1/{i.lower()}/proposals"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                                                         Chrome/73.0.3683.103 Safari/537.36',
                               'Accept': 'application/json'
                               }
                    data = get(url, headers=headers).json()
                    
                    try:
                        for j in data:
                            if j['proposal_status'] == 'PROPOSAL_STATUS_VOTING_PERIOD' and iso8601.parse_date(j['submit_time'][:-1]) > self.now:
                                number = j['id']
                                title = j['title']
                                message = f"{i.upper()}\nProposal {number} is in voting stage!\n{title}" #no link in the Mintscan response.
                                DiscordWebhook(url=self.discord_url, content=message).execute()

                        # now let's update the timestamp so that only later proposals are caught.
                        self.now = datetime.now(tz=pytz.UTC)

                    except Exception as e:
                        print(e)

            sleep(3600) #check for new proposals every hour. Adjust to whatever is more appropriate.

parser = ArgumentParser()
parser.add_argument("validator", nargs='+', help='Usage: python3 standalone_governance_alerts.py VALIDATOR1 VALIDATOR2 etc.')
args = parser.parse_args()

if __name__ == '__main__':
    #Note: this isn't a thread, because as of Python3.9 the LCD query will trigger an exception ("can't register atexit after shutdown")
    #I didn't find a solution to this. It worked with Python3.8 and is possibly resolved with Pyhon3.10, haven't tested.
    GetNewTerraProposals().run(args.validator)