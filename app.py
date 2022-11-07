from concurrent.futures import ThreadPoolExecutor
import threading
import string

from flask import Flask, request, jsonify
from secrets import SystemRandom

from shitty_bank_api import ShittyBankApi


app = Flask(__name__)

rand = SystemRandom()
executor = ThreadPoolExecutor(4)
shitty_bank_api = ShittyBankApi()


@app.route('/transfer', methods=['POST'])
def transfer_post():
    data = request.json
    amount, from_iban, to_iban = data['amount'], data['from_iban'], data['to_iban']
    assert isinstance(from_iban, str)
    assert isinstance(to_iban, str)
    assert isinstance(amount, str)
    amount = int(amount)
    assert amount > 0

    t = threading.Thread(target=transfer, args=(from_iban, to_iban, amount))
    t.daemon = True
    t.start()

    return jsonify(dict(result='success'))


def transfer(from_iban, to_iban, amount):
    wallet_id = create_wallet_id()
    shitty_bank_api.create_wallet(wallet_id)
    shitty_bank_api.settle(amount, wallet_id, "payin", from_iban)
    shitty_bank_api.settle(amount, wallet_id, "payout", to_iban)


def create_wallet_id():
    return 'myapp' + ''.join(rand.choice(string.ascii_lowercase) for _ in range(10))


if __name__ == '__main__':
    app.run()
