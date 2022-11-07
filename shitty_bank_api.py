from urllib3.util.retry import Retry
import requests
from requests.adapters import HTTPAdapter
from time import time


class ShittyBankApi:
    # All the callers should be blocked from calling for some time if the previous call failed
    # Tried using circuit circuitbreaker==1.4.0 since that would have been better
    # but I had issues installing it on a windows machine
    def __init__(self):
        self.url = "http://localhost:5001"
        self.session = requests.Session()
        retries = Retry(total=100,
                        backoff_factor=6,
                        status_forcelist=[500, 502, 503, 504],
                        method_whitelist=frozenset(['GET', 'POST']))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.min_event_id = 1
        self.max_transaction_time = 10
        self.wallet_history = {}

    def create_wallet(self, id):
        response = self.session.post(f"{self.url}/wallet/{id}")
        # if the result is "failure" we know that the wallet is created
        while response.json()["result"] != "error":
            response = self.session.post(f"{self.url}/wallet/{id}")

    def settle(self, amount, wallet_id, type, iban):
        self.session.post(f"{self.url}/settle", json={
            "amount": str(amount),
            "wallet_id": wallet_id,
            "type": type,
            "iban": iban
        })
        while not self.check_wallet(amount if type == "payin" else -amount, wallet_id, time()):
            return self.settle(amount, wallet_id, type, iban)

    def check_wallet(self, amount, wallet_id, start_time):
        if self.__check_sum_in_wallet(amount, wallet_id):
            return True

        is_last_check = time() - start_time > self.max_transaction_time

        response_dict = self.session.get(f"{self.url}/events/{self.min_event_id}").json()
        while response_dict["result"] != "success" or "events" not in response_dict or len(response_dict["events"]) == 0:
            response_dict = self.session.get(f"{self.url}/events/{self.min_event_id}").json()

        wallet_history = {d["wallet_id"]: d["amount"] for d in response_dict["events"] if d["wallet_id"].startswith("myapp")}
        self.min_event_id = response_dict["events"][-1]["event_id"]
        for wallet_history_item_id in wallet_history:
            if wallet_history_item_id in self.wallet_history:
                self.wallet_history[wallet_history_item_id].append(amount)
            else:
                self.wallet_history[wallet_history_item_id] = [amount]

        if is_last_check:
            return self.__check_sum_in_wallet(amount, wallet_id)
        return self.check_wallet(amount, wallet_id, start_time)

    def __check_sum_in_wallet(self, amount, wallet_id):
        if wallet_id in self.wallet_history and amount in self.wallet_history[wallet_id]:
            if sum(self.wallet_history[wallet_id]) == 0:
                del self.wallet_history[wallet_id]
            return True
        return False
