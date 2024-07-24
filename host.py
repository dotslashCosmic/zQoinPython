#Author: dotslashCosmic
import hashlib, time, json, requests, os
from flask import Flask, jsonify, request
from decimal import Decimal
from client import BlockchainGUI

client_port = 5317
host_port = 5318
full_name = "zQoin"
client_version = "2e6ab0376ea2feae2bdc0734cf03304f3cc9623f9d74ab1363633f4ba493fa71d248e53819d1dffe120d75370e1fd1edd5da9da7f5a245df66c36ee320d618fe"

class Block:
    def __init__(self, index, previous_hash, timestamp, data, hash, nonce):
        self.index = index
        cur_index = self.index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash
        self.nonce = nonce

def calculate_hash(index, previous_hash, timestamp, data, nonce):
    value = str(index) + str(previous_hash) + str(timestamp) + str(data) + str(nonce)
    return hashlib.sha3_512(value.encode('utf-8')).hexdigest()

def create_genesis_block():
    index, previous_hash = 0, 0
    timestamp = int(time.time())
    nonce = int.from_bytes(os.urandom(8), 'big')
    genesis = hashlib.sha3_512((str(timestamp)+full_name+str(nonce)+"GENESIS").encode()).hexdigest()
    hash = calculate_hash(index, previous_hash, timestamp, genesis, nonce)
    return Block(index, previous_hash, timestamp, genesis, hash, nonce)

class Blockchain:
    def __init__(self):
        self.chain = []
        self.balances = {}
        self.difficulty, self.target, self.max_base = self.get_difficulty_and_target()
        self.load_chain()
        self.transaction_pool = []
        self.nonce = self.nonce_chain()

    def save_chain(self):
        with open('blockchain.json', 'w') as f:
            chain_data = []
            seen_indexes = set()
            for block in self.chain:
                if block.index not in seen_indexes:
                    block_data = {
                        "index": block.index,
                        "timestamp": block.timestamp,
                        "previous_hash": block.previous_hash,
                        "data": block.data,
                        "hash": block.hash,
                        "nonce": block.nonce,
                    }
                    chain_data.append(block_data)
                    seen_indexes.add(block.index)
            json.dump({'chain': chain_data, 'balances': self.balances}, f)

    def load_chain(self):
        try:
            with open('blockchain.json', 'r') as f:
                data = json.load(f)
                self.chain = [Block(
                    block['index'],
                    block['timestamp'],
                    block['previous_hash'],
                    block.get('data', 'GENESISzQoinGENESIS'),
                    block['hash'],
                    block['nonce'],
                ) for block in data['chain']]
                self.balances = data['balances']
        except FileNotFoundError:
            self.chain.append(create_genesis_block())
            self.balances["0"] = 0
            
    def get_difficulty_and_target(self):
        if self.chain:
            index = self.chain[-1].index
        else:
            index = 0
        base = 1e8
        max_base = 1e12
        a = 9999
        b = 999
        c = 99
        d = 1.999
        e = 99999
        base_difficulty = base + (index * a) 
        additional_difficulty = (index // b) * e
        exponential_difficulty = int((index // c) ** d)
        difficulty = base_difficulty + additional_difficulty + exponential_difficulty
        target = '0' * int(difficulty)
        if difficulty >= max_base:
            print(f"Reached the maximum limit of {index} zQoin in circulation.")
        return difficulty, target, max_base
        
    def get_latest_block(self):
        return self.chain[-1]

    def get_latest_index(self):
        return self.get_latest_block().index
        
    def nonce_chain(self):
        try:
            self.load_chain()
            return self.chain[-1].nonce if self.chain else 0
        except FileNotFoundError:
            self.chain.append(create_genesis_block())
            self.balances["0"] = 0
            return self.chain[-1].nonce

    def proof_of_work(self, index, previous_hash, timestamp, data):
        nonce = self.nonce_chain()
        difficulty, _, _ = self.get_difficulty_and_target()
        while True:
            hash = calculate_hash(index, previous_hash, timestamp, data, nonce)
            if hash[:int(difficulty)] == '0' * int(difficulty):
                return nonce, hash
            nonce += 1

    def add_block(self, miner_address):
        previous_block = self.get_latest_block()
        index = previous_block.index + 1
        timestamp = int(time.time())
        previous_hash = previous_block.hash
        data = json.dumps(self.transaction_pool)
        nonce, hash = self.proof_of_work(index, previous_hash, timestamp, data)
        new_block = Block(index, previous_hash, timestamp, data, hash, nonce)
        self.chain.append(new_block)
        for transaction in self.transaction_pool:
            self.update_balances(transaction, miner_address)
        self.transaction_pool = []
        self.save_chain()

    def update_balances(self, transaction, miner_address):
        sender = transaction['sender']
        receiver = transaction['receiver']
        amount = float(transaction['amount'])
        if sender != "0":
            if sender not in self.balances:
                self.balances[sender] = 0
            self.balances[sender] -= amount
        if receiver not in self.balances:
            self.balances[receiver] = 0
        self.balances[receiver] += amount
        if miner_address not in self.balances:
            self.balances[miner_address] = 0
        self.balances[miner_address] += 1

app = Flask(__name__)
print("Loading Blockchain...")
blockchain = Blockchain()
difficulty, _, _ = blockchain.get_difficulty_and_target()
print("Blockchain initialized.\nCurrent block:", blockchain.get_latest_index(), "\nNext block difficulty:", difficulty)

@app.route('/difficulty', methods=['GET'])
def get_difficulty():
    difficulty, target, max_base = blockchain.get_difficulty_and_target()
    if difficulty >= max_base:
        print(f"Reached the maximum limit of zQoin in circulation.")
        return jsonify({'difficulty': None, 'target': None})
    else:
        return jsonify({'difficulty': difficulty, 'target': target, 'max_base': max_base})

@app.route('/transactions', methods=['POST'])
def add_transaction():
    transaction = request.get_json()
    blockchain.transaction_pool.append(transaction)
    return jsonify(transaction), 201

@app.route('/send_transaction', methods=['POST'])
def send_transaction():
    miner_address = request.get_json().get('miner_address')
    blockchain.add_block(miner_address)
    return jsonify(blockchain.get_latest_block().__dict__), 201

blockchain = Blockchain()
@app.route('/blocks', methods=['GET'])
def get_blocks():
    chain_data = []
    seen_hashes = set()
    last_blocks = blockchain.chain[-10:]
    for block in last_blocks:
        if block.hash not in seen_hashes:
            chain_data.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "hash": block.hash
            })
            seen_hashes.add(block.hash)
    return jsonify(chain_data)

@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = []
    for block in blockchain.chain:
        transactions.append(block.data)
    return jsonify(transactions)

@app.route('/add_block', methods=['POST'])
def add_block():
    #if 500/RemoteDisconnected risen, dump packet and do not save the blockchain or send rewards
    difficulty, _, _ = blockchain.get_difficulty_and_target()
    block_data = request.json
    data = block_data['data']
    hash = block_data['hash']
    miner = block_data['miner']
    first_hash = data.split('[')[0]
    old_hash = blockchain.get_latest_block().hash
    if not first_hash == old_hash:
        return jsonify({"message": "Block declined"}), 400
    previous_block = blockchain.get_latest_block()
    index = previous_block.index + 1
    hash_rate = block_data['hash_rate']
    timestamp = int(time.time())
    previous_hash = previous_block.hash
    nonce = blockchain.nonce_chain()
    new_block = Block(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest(), hash, nonce)
    blockchain.chain.append(new_block)
    blockchain.save_chain()
    print(f"Block {index} at difficulty {difficulty} ready to mine.")
    data = {
        'message': "approved",
        'address': miner,
        'amount': 1
    }
    #TODO Update to grab the miners IP address instead of localhost
    response = requests.post(f'http://localhost:{client_port}/update_wallet', json=data)
    if response.status_code == 200:
        with open('hostwallet.json', 'r') as f:
            host_wallets = json.load(f)
        for wallet in host_wallets:
            if wallet['public_key'] == miner:
                wallet['amount'] = int(wallet['amount'])
                wallet['amount'] += 1
                break
        with open('hostwallet.json', 'w') as f:
            json.dump(host_wallets, f, indent=4)
        return jsonify({"message": f"Block {index} mined successfully!"}), 200
    else:
        print("Failed to send mining pool rewards.")
        return jsonify({"message": "Failed to send mining pool rewards."}), 500
        #TODO Retroactively queue bad rewards for future attempts

@app.route('/latest_block', methods=['GET'])
def latest_block():
    latest_block = blockchain.get_latest_block()
    block_data = {
        "index": latest_block.index,
        "timestamp": latest_block.timestamp,
        "previous_hash": latest_block.previous_hash,
        "data": latest_block.data,
        "hash": latest_block.hash,
        "nonce": latest_block.nonce,
    }
    return jsonify(block_data), 200
    
@app.route('/check_client', methods=['POST'])
def check_client():
    data = request.get_json()
    client_hash = data.get('client_hash')
    coin_name = data.get('coin_name')
    client_wallet = data.get('client_wallet')
    if client_hash == client_version and coin_name == full_name:
        return jsonify({"status": "success"}), print(f"{client_wallet} is verified.")
    else:
        #On failure, remove the wallet that was just created, if there was a creation that just happened with that wallet address
        return jsonify({"status": "failure"}), print(f"{client_wallet} failure to verify: {client_hash}")
        
@app.route('/wallet_exists', methods=['POST'])
def wallet_exists():
    data = request.get_json()
    public_key = data.get('public_key')
    try:
        with open('hostwallet.json', 'r') as f:
            wallets = json.load(f)
        for wallet in wallets:
            if wallet['public_key'] == public_key:
                return jsonify({'exists': True})
    except FileNotFoundError:
        with open('hostwallet.json', 'w') as f:
            json.dump([], f)
        return jsonify({'exists': False})

@app.route('/get_wallet', methods=['POST'])
def get_wallet():
    data = request.get_json()
    public_key = data.get('public_key')
    with open('hostwallet.json', 'r') as f:
        wallets = json.load(f)
    for wallet in wallets:
        if wallet['public_key'] == public_key:
            return jsonify({
                'private_key': wallet['private_key'],
                'public_key': wallet['public_key'],
                'amount': wallet['amount']
            })
    return jsonify({'error': 'Wallet not found.'}), 404
    
@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    data = request.get_json()
    if isinstance(data, list):
        for wallet_data in data:
            mnemonic = wallet_data.get('mnemonic')
            seed = wallet_data.get('seed')
            private_key = wallet_data.get('private_key')
            public_key = wallet_data.get('public_key')
            nickname = wallet_data.get('nickname')
            try:
                with open('hostwallet.json', 'r') as f:
                    wallets = json.load(f)
            except FileNotFoundError:
                wallets = []
            wallets.append({
                'mnemonic': mnemonic,
                'seed': seed,
                'private_key': private_key,
                'public_key': public_key,
                'nickname': nickname,
                'amount': '0'
            })
            with open('hostwallet.json', 'w') as f:
                json.dump(wallets, f, indent=4)
        return jsonify({'message': f'Wallet {public_key} created.'})
    else:
        return jsonify({'error': 'Invalid data format.'}), 400

@app.route('/add_amount', methods=['POST'])
def add_amount():
    data = request.get_json()
    public_key = data.get('public_key')
    amount = data.get('amount')
    with open('hostwallet.json', 'r') as f:
        wallets = json.load(f)
    for wallet in wallets:
        if wallet['public_key'] == public_key:
            wallet['amount'] += amount
            break
    with open('hostwallet.json', 'w') as f:
        json.dump(wallets, f, indent=4)
    return jsonify({'message': 'Amount added successfully'})
    
if __name__ == '__main__':
    print("zQoin Node Initialized.")
    app.run(port=host_port)
