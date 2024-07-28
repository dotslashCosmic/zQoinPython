#Author: dotslashCosmic
import hashlib, time, json, requests, os, sys, math, secrets
from flask import Flask, jsonify, request
from collections import defaultdict

consensus_results = defaultdict(list) #Initialize
client_port = 5317 #int 1-65535
host_port = 5318 #int 1-65535
base = 1e5 #Base difficulty, ~2s @500H/s
max_base = 1e9 #Maximum difficulty, ~30m @500H/s
a = 3 #lower is easier, int 1-1000, Additive, base additive per block
b = 13 #higher is easier, int 1-100, Additive, Every b blocks, add e
c = 27 #higher is easier, int 1-100, Additive, Every c blocks, * d
d = 1.1 #lower is easier, float 1.0-10.0, Exponential multiplier
e = 3 #lower is easier, int 1-100, How much to add every b blocks
max_coin = 10000000 #Maximum amount of coins in circulation, ~462mb per 1m max_coin/reward, ~580 bytes per wallet
reward = 1.00000000 #Base coin reward, float
decimals = 8 #Maximum trailing decimals for reward, int 0-8, max of 8
time_between_rewards = 15 #Minimum seconds between blocks, to prevent flooding, allows more consensuses
consensus_count = 1 #Minimum verifications for consensus
coin_name = "zQoin" #Coin full name
short_name = "zqn" #Coin short name(lowercase/numbers)
wallet_list_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/wordlist/en.txt" #Wallet creation word list
host_version_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/hash/host.sha3_512" #SHA3-512 of this file
check = True #Bool, validate host with host_version_url
client_version = "dac7f3c598177f7b7f3b1d89bce5cdf8a3703aa5f007b8b66aa64a041a28851933bb0dab5398fb7cf63bae44c2b45b6d6636d9d64c16d14f978c084a8e60bdfa" #SHA3-512 of client.py
genesis_token = f'{client_version}{coin_name}GENESIS' #Genesis block

def create_genesis_block():
    index, previous_hash = 0, 0
    timestamp = int(time.time())
    nonce = int.from_bytes(os.urandom(8), 'big')
    genesis = hashlib.sha3_512((str(timestamp)+str(nonce)+genesis_token).encode()).hexdigest()
    hash = hashlib.sha3_512((str(index)+str(previous_hash)+str(timestamp)+str(nonce)).encode('utf-8')).hexdigest()
    return Block(index, previous_hash, timestamp, genesis, hash, nonce)

def entropy_to_mnemonic(entropy, wordlist):
    entropy_bits = bin(int.from_bytes(entropy, byteorder='big'))[2:].zfill(len(entropy) * 8)
    checksum_length = len(entropy_bits) // 32
    checksum = bin(int(hashlib.sha3_512(entropy).hexdigest(), 16))[2:].zfill(512)[:checksum_length]
    bits = entropy_bits + checksum
    words = [wordlist[int(bits[i:i+11], 2)] for i in range(0, len(bits), 11)]
    return ' '.join(words)
    
with open(__file__, 'rb') as file:
    our_version = hashlib.sha3_512(file.read()).hexdigest()
    print(f"Host version: {our_version}")
if check == True:
    print("Host check enabled.")
    response = requests.get(host_version_url)
    if response.status_code == 200:
        host_version = response.text.strip()
        if host_version != our_version:
            print(f"{coin_name} version mismatch.")
            sys.exit(1)
        else:
            print(f"{coin_name} version match!")
    else:
        print("Failed to fetch host version.")
        sys.exit(1)
else:
    line = '~' * 29
    print(f"{line}\nWARNING! Host check disabled!\n{line}")
if client_port == host_port:
    print(f"Client port {client_port} and host port {host_port} cannot be the same.")
    sys.exit(1)
reward_str = str(reward)
if '.' in reward_str:
    integer_part, decimal_part = reward_str.split('.')
    if len(decimal_part) > decimals:
        print(f"Trailing decimal for {reward} is longer than {decimals}.")
        sys.exit(1)
if not (1 <= len(short_name) <= 5 and all(char.islower() or char.isdigit() for char in short_name)):
    print("Short name must be between 1 and 5 characters and only contain lowercase letters and digits.")
    sys.exit(1)

class Block:
    def __init__(self, index, previous_hash, timestamp, data, hash, nonce):
        self.index = index
        cur_index = self.index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash
        self.nonce = nonce

class Blockchain:
    def __init__(self):
        self.chain = []
        self.balances = {}
        self.max_base = max_base
        self.difficulty, self.target, self.limit = self.get_difficulty_and_target()
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
        base_difficulty = base + (index * a) 
        additional_difficulty = int(index // b) * e
        exponential_difficulty = int((index // c) ** d)
        difficulty = base_difficulty+additional_difficulty+exponential_difficulty
        difficulty = int(difficulty)        
        target = '0' * int(difficulty)
        if index >= (max_coin/reward) or difficulty >= self.max_base:
            difficulty, max_base = 1, 2
            target = '0' * int(difficulty)
            limit = True
            return difficulty, target, limit
        limit = False
        return difficulty, target, limit
        
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

app = Flask(__name__)
print("Loading blockchain...")
blockchain = Blockchain()
difficulty, target, limit = blockchain.get_difficulty_and_target()
print(f"Blockchain initialized.\nCurrent block: {blockchain.get_latest_index()}\nNext block difficulty: {difficulty}")

@app.route('/difficulty', methods=['GET'])
def get_difficulty():
    difficulty, target, limit = blockchain.get_difficulty_and_target()
    nonce = blockchain.nonce
    transactions = []    
    if limit == True:
        print(f"Reached the maximum limit of {max_coin} {coin_name} in circulation.")
        return jsonify({'difficulty': difficulty, 'target': target, 'max_base': max_base, 'transactions': transactions, 'nonce': nonce, 'limit': True}), 200
    else:
        for block in blockchain.chain:
            transactions.append(block.data)
        return jsonify({'difficulty': difficulty, 'target': target, 'max_base': max_base, 'transactions': transactions, 'nonce': nonce, 'limit': False}), 200


blockchain = Blockchain()
@app.route('/blocks', methods=['GET'])
def get_blocks():
    try:
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
        return jsonify(chain_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
last_reward_time = time.time()
@app.route('/add_block', methods=['POST'])
def add_block():
#Start transaction consensus integration
    global last_reward_time
    try:
        difficulty, _, limit = blockchain.get_difficulty_and_target()
        if difficulty == base:
            difficulty_time = time.time()
            while time.time() - difficulty_time < time_between_rewards:
                time.sleep(time_between_rewards)
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
        while time.time() - last_reward_time < time_between_rewards:
            time.sleep(0.01)
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
                if limit == True:
                    reward_per_miner = float(0)
                elif limit == False:
                    reward_per_miner = float(f"{(reward ** math.factorial(consensus_count)) / consensus_count:.{decimals}f}")
                print(f"Block {index} mined: {new_hash}\nReward per miner: {reward_per_miner:.{decimals}f} {coin_name}")
                for address, result in consensus_results[index].items():
                    data = {
                        'message': "approved",
                        'address': address,
                        'decimals': decimals,
                        'amount': float(f"{reward_per_miner:.{decimals}f}")
                    }
                    miner_ip = request.remote_addr
                    response = requests.post(f'http://{miner_ip}:{client_port}/update_wallet', json=data)
                    print(f"Sent {reward_per_miner} to {address}, response status: {response.status_code}")
                    if response.status_code == 200:
                        with open('hostwallet.json', 'r') as f:
                            host_wallets = json.load(f)
                        for wallet in host_wallets:
                            if wallet['public_key'] == address:
                                wallet['amount'] = float(wallet['amount']) + float(reward_per_miner)
                                wallet['amount'] = f"{wallet['amount']:.{decimals}f}"
                                break
                        with open('hostwallet.json', 'w') as f:
                            json.dump(host_wallets, f, indent=4)
                del consensus_results[index]
                last_reward_time = time.time()
                new_index = index + 1
                difficulty, _, _ = blockchain.get_difficulty_and_target()
                print(f"Block {new_index} ready to mine at difficulty {difficulty}!")
                return jsonify({"message": f"Consensus achieved. Block {index} mined successfully!"}), 200
            else:
                print("Block flooding detected.")
                return jsonify({"message": "Block flooding detected."}), 400
        else:
            print("Consensus not reached yet.")
            return jsonify({"message": "Waiting for consensus."}), 202
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
                return jsonify({'exists': True}), 200
        return jsonify({'exists': False}), 200
    except FileNotFoundError:
        with open('hostwallet.json', 'w') as f:
            json.dump([], f)
        return jsonify({'exists': False}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                'amount': float(wallet['amount'])
            })
    return jsonify({'error': 'Wallet not found.'}), 400
    
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
            r_coin_name = wallet_data.get('coin_name')
            if not public_key.startswith(short_name) and r_coin_name != coin_name:
                return jsonify({'exists': False, 'message': f'{public_key} is invalid.'}), 400
            wallet_data.pop('coin_name', None)
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
    amount = float(data.get('amount'))
    try:
        with open('hostwallet.json', 'r') as f:
            wallets = json.load(f)
        for wallet in wallets:
            if wallet['public_key'] == public_key:
                wallet['amount'] += float(amount)
                break
        with open('hostwallet.json', 'w') as f:
            json.dump(wallets, f, indent=4)
        return jsonify({'message': f'{amount} added to {public_key}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/wallet_list', methods=['GET'])
def wallet_list():
    response = requests.get(wallet_list_url)
    if response.status_code == 200:
        wordlist = response.text.splitlines()
        entropy = secrets.token_bytes(128 // 8)
        mnemonic = entropy_to_mnemonic(entropy, wordlist)
        return jsonify({'mnemonic': mnemonic}), 200
    else:
        return jsonify({'error': 'Failed to fetch wordlist.'}), 500

if __name__ == '__main__':
    print(f"{coin_name} Node Initialized.")
    app.run(port=host_port)
