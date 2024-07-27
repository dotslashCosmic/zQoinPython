#Author: dotslashCosmic
import hashlib, time, json, requests, os, sys
from flask import Flask, jsonify, request
from decimal import Decimal
from client import BlockchainGUI
from collections import defaultdict

client_port = 5317 #int 1-65535
host_port = 5318 #int 1-65535
if client_port == host_port:
    print("Client and host port cannot be the same.")
    sys.exit(1)
reward = 10 #int, Block reward
time_between_rewards = 1 #Minimum seconds between rewards, to prevent block flooding
consensus_count = 1 #Minimum verifications for consensus
coin_name = "zQoin" #Coin full name
short_name = 'zqn' #Coin short name
if not (len(short_name) == 3 and all(char.islower() or char.isdigit() for char in short_name)):
    print("Short name must be 3 characters and only contain lowercase letters and digits.")
    sys.exit(1)
genesis_token = f'GENESIS{coin_name}GENESIS' #Genesis block
consensus_results = defaultdict(list) #Initialize
client_version = "dcf4e61f9c253283100d81c4ae13e44c048a89169c13278a5789fad14b3d1c730cf9d0c85d38e7007d87e2fb463d375cdcdd5171b1a416e65157fed7c102b574" #SHA3-512 of client.py

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
    value = str(index)+str(previous_hash)+str(timestamp)+str(data)+str(nonce)
    return hashlib.sha3_512(value.encode('utf-8')).hexdigest()

def create_genesis_block():
    index, previous_hash = 0, 0
    timestamp = int(time.time())
    nonce = int.from_bytes(os.urandom(8), 'big')
    genesis = hashlib.sha3_512((str(timestamp)+str(nonce)+genesis_token).encode()).hexdigest()
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
                    block.get('data', genesis_token),
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
        base = 10000
        max_base = 100000000
        a = 3
        b = 13
        c = 27
        d = 1.1
        e = 3
        base_difficulty = base + (index * a) 
        additional_difficulty = (index // b) * e
        exponential_difficulty = int((index // c) ** d)
        difficulty = base_difficulty+additional_difficulty+exponential_difficulty
        target = '0' * int(difficulty)
        if difficulty >= max_base:
            print(f"Reached the maximum limit of {index} {full_name} in circulation.")
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
        self.balances[miner_address] += reward

app = Flask(__name__)
print("Loading blockchain...")
blockchain = Blockchain()
difficulty, _, _ = blockchain.get_difficulty_and_target()
print(f"Blockchain initialized.\nCurrent block: {blockchain.get_latest_index()}\nNext block difficulty: {difficulty}")

@app.route('/difficulty', methods=['GET'])
def get_difficulty():
    difficulty, target, max_base = blockchain.get_difficulty_and_target()
    nonce = blockchain.nonce
    transactions = []    
    if difficulty >= max_base:
        print(f"Reached the maximum limit of {coin_name} in circulation.")
        return jsonify({'difficulty': None, 'target': None, 'max_base': None, 'transactions': None, 'nonce': None})
    else:
        for block in blockchain.chain:
            transactions.append(block.data)
        return jsonify({'difficulty': difficulty, 'target': target, 'max_base': max_base, 'transactions': transactions, 'nonce': nonce})

@app.route('/transactions', methods=['POST'])
def add_transaction():
    transaction = request.get_json()
    blockchain.transaction_pool.append(transaction)
    return jsonify(transaction), 201

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
    
last_reward_time = 0
@app.route('/add_block', methods=['POST'])
def add_block():
#Start transaction consensus integration
    global last_reward_time
    try:
        difficulty, _, _ = blockchain.get_difficulty_and_target()
        block_data = request.json
        data = block_data['data']
        received_nonce = block_data['new_nonce']
        new_hash = block_data['new_hash']
        new_transactions = block_data['new_transactions']
        miner = block_data['miner']
        first_hash = data.split('[')[0]
        old_hash = blockchain.get_latest_block().hash
        previous_block = blockchain.get_latest_block()
        index = previous_block.index + 1
        hash_rate = block_data['hash_rate']
        timestamp = int(time.time())
        previous_hash = previous_block.hash
        result = (data, received_nonce, new_hash, first_hash)
        if index not in consensus_results:
            consensus_results[index] = {}
        if miner not in consensus_results[index]:
            consensus_results[index][miner] = result
        else:
            return jsonify({"message": f"Miner {miner} has already verified consensus block {index}"}), 400
        matching_results = []
        print(f"Consensus {len(matching_results)+1}/{consensus_count} for block {index} from miner {miner}")
        for block_index, block_consensus in consensus_results.items():
            if block_index == index:
                for address, result in block_consensus.items():
                    matching_results.append(result)
        if len(matching_results) >= consensus_count:
            if time.time() - last_reward_time >= time_between_rewards:
                received_nonce + 1
                new_block = Block(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest(), new_hash, received_nonce)
                blockchain.chain.append(new_block)
                blockchain.save_chain()
                reward_per_miner = reward / len(matching_results)
                print(f"Block {index} mined!\nReward per miner: {reward_per_miner}")
                for address, result in consensus_results[index].items():
                    data = {
                        'message': "approved",
                        'address': address,
                        'amount': reward_per_miner
                    }
                    miner_ip = request.remote_addr
                    response = requests.post(f'http://{miner_ip}:{client_port}/update_wallet', json=data)
                    print(f"Sent reward to {address}, response status: {response.status_code}")
                    if response.status_code == 200:
                        with open('hostwallet.json', 'r') as f:
                            host_wallets = json.load(f)
                        for wallet in host_wallets:
                            if wallet['public_key'] == address:
                                wallet['amount'] = float(wallet['amount'])
                                wallet['amount'] += reward_per_miner
                                break
                        with open('hostwallet.json', 'w') as f:
                            json.dump(host_wallets, f, indent=4)
                del consensus_results[index]
                last_reward_time = time.time()
                return jsonify({"message": f"Block {index} mined successfully!"}), 200
            else:
                print("Block flooding detected.")
                return jsonify({"message": "Block flooding detected."}), 400
        else:
            print("Consensus not reached.")
            return jsonify({"message": "Consensus not reached."}), 400
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        print(f"Error: {e}")
        return jsonify({"message": "Block declined due to connection error."}), 400
        
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
    if client_hash == client_version:
        return jsonify({"message": "Client verified!"}), 200
    else:
        #On failure, remove the wallet that was just created, if there was a creation that just happened with that wallet address
        return jsonify({"message": "Client verification failed."}), 400
        
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
        return jsonify({'message': f'Wallet {public_key} created!'}), 200
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
    return jsonify({'message': 'Amount added successfully!'}), 200
    
if __name__ == '__main__':
    print(f"{coin_name} Node Initialized.")
    app.run(port=host_port)