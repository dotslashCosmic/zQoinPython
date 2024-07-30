#Author: dotslashCosmic v0.1.0
import hashlib, time, json, requests, os, sys, math, secrets, threading
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from collections import defaultdict
from ipaddress import ip_address
from urllib.parse import urlparse
from enum import Enum

coin_name = "zQoin" #Coin full name
short_name = "zqn" #Coin short name(lowercase/numbers, up to 5 chars)
client_port = 5317 #int 1-65535
host_port = 5318 #int 1-65535
base = 100000 #Base difficulty, ~2s @500H/s
max_base = 1000000000 #Maximum difficulty, ~30m @500H/s
a = 3 #lower is easier, int 1-1000, Additive, base additive per block
b = 13 #higher is easier, int 1-100, Additive, Every b blocks, add e
c = 27 #higher is easier, int 1-100, Additive, Every c blocks, * d
d = 1.1 #lower is easier, float 1.0-10.0, Exponential multiplier
e = 3 #lower is easier, int 1-100, How much to add every b blocks
max_coin = 10000000 #Maximum amount of coins in circulation, ~462mb per 1m max_coin/reward, ~580 bytes per wallet
reward = 1.00000000 #Base coin reward, float
decimals = 8 #Maximum trailing decimals for reward, int 0-8, absolute limit of 8
time_between_rewards = 15 #Minimum seconds between blocks, int
consensus_count = 1 #Minimum verifications for consensus per node
node_consensus = 2 #Minimum nodes for consensus verification
node_tolerance = 0 #Tolerance for faulty/malicious nodes
wallet_list_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/wordlist/en.txt" #Wallet creation word list
host_version_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/hash/host.sha3_512" #SHA3-512 of this file
check = False #Bool, validate host/client with host_version_url/client_version
local = True #Bool, allows local IPs
node_dns = 'localhost' # DNS resolve to nodes list, in progress
client_version = "b43c381f24f39a8e7b1f69090f423f82d99905239f93aff403f5d47aaa48cc2374eec5b615937e4b404900bb7bf8663aa85668d8c85b65db290ec280a49046ea" #SHA3-512 of client.py
genesis_token = f'{client_version}{coin_name}GENESIS' #Genesis block
consensus_results = defaultdict(list) #Initialize

def create_genesis_block():
    index, previous_hash = 0, 0
    timestamp = int(time.time())
    nonce = int.from_bytes(os.urandom(8), 'big')
    genesis = hashlib.sha3_512((str(timestamp)+str(nonce)+genesis_token).encode()).hexdigest()
    hash = hashlib.sha3_512((str(index)+str(previous_hash)+str(timestamp)+str(nonce)).encode('utf-8')).hexdigest()
    request = json.dumps({
        'index': index,
        'previous_hash': previous_hash,
        'timestamp': timestamp,
        'genesis': genesis,
        'hash': hash,
        'nonce': nonce
    })
    return Block(index, previous_hash, timestamp, genesis, hash, nonce)

def entropy_to_mnemonic(entropy, wordlist):
    entropy_bits = bin(int.from_bytes(entropy, byteorder='big'))[2:].zfill(len(entropy) * 8)
    checksum_length = len(entropy_bits) // 32
    checksum = bin(int(hashlib.sha3_512(entropy).hexdigest(), 16))[2:].zfill(512)[:checksum_length]
    bits = entropy_bits + checksum
    words = [wordlist[int(bits[i:i+11], 2)] for i in range(0, len(bits), 11)]
    return ' '.join(words)

def bootup(__file__, check, host_version_url, coin_name, client_port, host_port, a, b, c, e, d, reward, decimals, short_name, time_between_rewards, consensus_count, base, max_base):
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
    for port, p_name in [(client_port, "Client"), (host_port, "Host")]:
        if not isinstance(port, int) or not (1 <= port <= 65535):
            print(f"{p_name} port {port} is not a valid port number. It must be an integer between 1 and 65535.")
            sys.exit(1)
    if client_port == host_port:
        print(f"Client port {client_port} and host port {host_port} cannot be the same.")
    for var, name in [(a, "a"), (b, "b"), (c, "c"), (e, "e")]:
        if not isinstance(var, int) or var < 1:
            print(f"'{name}' must be an integer and at least 1. Current value: {var}")
            sys.exit(1)
        if var > 1e5:
            print(f"Warning! Variable {name} is very large ({var}). Consider using a smaller value.")
    if not isinstance(node_consensus, int) or node_consensus < 1:
        print(f"'node_consensus' must be an integer and at least 1. Current value: {node_consensus}")
        sys.exit(1)
    if not isinstance(node_tolerance, int) or node_tolerance < 0:
        print(f"'node_tolerance' must be an integer and at least 0. Current value: {node_tolerance}")
        sys.exit(1)
    if node_tolerance >= node_consensus:
        print(f"'node_tolerance' must be equal to or less than 'node_consensus'. node_tolerance: {node_tolerance}, node_consensus {node_consensus}")
        sys.exit(1)
    if node_tolerance < node_consensus / 2:
        print(f"Warning! 'node_tolerance' is very low ({node_tolerance}). Consider using a higher value of at least {node_consensus // 2 + 1}.")
    if node_tolerance > node_consensus * 0.75:
        print(f"Warning! 'node_tolerance' is very high ({node_tolerance}). Consider using a lower value of at most {int(node_consensus * 0.75)}.")
    if not isinstance(decimals, int) or not (0 <= decimals <= 8):
        print(f"'decimals' must be an integer between 0 and 8. Current value: {decimals}")
        sys.exit(1)
    if not isinstance(d, float) or d < 1.0:
        print(f"'d' must be a float up to decimal {decimals}, and at least 1.0. Current value: {d}")
        sys.exit(1)
    if d > 5.0:
        print(f"Warning! 'd' is very large ({d}). Consider using a smaller value.")
    reward_str = str(reward)
    if '.' in reward_str:
        integer_part, decimal_part = reward_str.split('.')
        if len(decimal_part) > decimals:
            print(f"Trailing decimal for {reward} is longer than {decimals} decimals.")
            sys.exit(1)
    if not (1 <= len(short_name) <= 5 and all(char.islower() or char.isdigit() for char in short_name)):
        print("'short_name' must be between 1 and 5 characters and only contain lowercase letters and digits.")
        sys.exit(1)
    if decimals > 8:
        print(f"Warning! 'decimals' is very large ({decimals}). Consider using a smaller value.")
    if not isinstance(time_between_rewards, int) or time_between_rewards < 1:
        print(f"'time_between_rewards' must be an integer and at least 1. Current value: {time_between_rewards}")
        sys.exit(1)
    if time_between_rewards > 360:
        print(f"Warning! 'time_between_rewards' is very large ({time_between_rewards}) seconds. Consider using a smaller value.")
    if not isinstance(consensus_count, int) or consensus_count < 1:
        print(f"'consensus_count' must be an integer and at least 1. Current value: {consensus_count}")
        sys.exit(1)
    if consensus_count <= 3:
        print(f"Warning! 'consensus_count' is very low ({consensus_count}). Consider using a higher value of at least 3.")
    if not isinstance(base, int) or base < 1:
        print(f"'base' must be an integer and at least 1. Current value: {base}")
        sys.exit(1)
    if base > 10000000:
        print(f"Warning! 'base' is very large to start ({base}). Potential MemoryError.")
    if not isinstance(max_base, int) or max_base < 1:
        print(f"'max_base' must be an integer and at least 1. Current value: {max_base}")
        sys.exit(1)
    if max_base > 1000000000:
        print(f"Warning: 'max_base' is very large ({max_base}). Potential MemoryError.")

class NodeRole(Enum):
    PRIMARY = 1
    REPLICA = 2

class PBFTType(Enum):
    PRE_PREPARE = 1
    PREPARE = 2
    COMMIT = 3
    REPLY = 4

class PBFTMessage:
    def __init__(self, msg_type, view, seq_num, digest, node_id):
        self.msg_type = msg_type
        self.view = view
        self.seq_num = seq_num
        self.digest = digest
        self.node_id = node_id

class PBFTNode:
    def __init__(self, node_id, role, node_dns):
        self.node_id = node_id
        self.role = role
        self.view = 0
        self.seq_num = 0
        self.message_log = []
        self.prepared_messages = defaultdict(list)
        self.committed_messages = defaultdict(list)
        #TODO DNS list for trusted nodes, pick one at random, make sure it isnt this IP
        self.node_resolve = node_dns

    def reached_correct_consensus(self):
        for seq_num, messages in self.committed_messages.items():
            digests = [msg.digest for msg in messages]
            if len(set(digests)) > 1:
                self.alert_malicious(seq_num)
                self.committed_messages[seq_num] = [msg for msg in messages if msg.digest == digests[0]]
                return False
        #TODO Allow save the blockchain here, then wait/make sure all blockchains are saved before continuing, verify with the rest, and then allow the next block to be available
        print("Nodes have agreed on consensus.")
        blockchain.chain.append(new_block)
        self.synchronize_blockchains()
        return True

    def alert_malicious(self, seq_num):
        digests = [msg.digest for msg in self.committed_messages[seq_num]]
        malicious_digest = max(set(digests), key=digests.count)
        malicious_nodes = [msg.node_id for msg in self.committed_messages[seq_num] if msg.digest != malicious_digest]
        alert_msg = {'seq_num': seq_num, 'message': 'Malicious node detected', 'malicious_nodes': malicious_nodes}
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://'+self.node_resolve+':'+str(host_port)+'/node_alert'
                requests.post(url, json=alert_msg)
        
    def send_all(self, msg):
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://'+self.node_resolve+':'+str(host_port)+'/node_receive'
                requests.post(url, json=msg.__dict__)

    def receive_message(self, msg):
        msg = PBFTMessage(**msg)
        if msg.msg_type == PBFTType.PRE_PREPARE:
            self.prepare(msg)
        elif msg.msg_type == PBFTType.PREPARE:
            self.commit(msg)
        elif msg.msg_type == PBFTType.COMMIT:
            self.reply(msg)

    def pre_prepare(self, request):
        if self.role == NodeRole.PRIMARY:
            self.seq_num += 1
            digest = hashlib.sha3_512(request.encode()).hexdigest()
            msg = PBFTMessage(PBFTType.PRE_PREPARE, self.view, self.seq_num, digest, self.node_id)
            self.message_log.append(msg)
            print(f"Pre-prepare result: {msg}")
            self.send_all(msg)

    def prepare(self, msg):
        if self.role == NodeRole.REPLICA:
            self.message_log.append(msg)
            self.prepared_messages[msg.seq_num].append(msg)
            if len(self.prepared_messages[msg.seq_num]) >= 2 * f:
                print(f"Prepare result: {msg}")
                self.commit(msg)

    def commit(self, msg):
        self.committed_messages[msg.seq_num].append(msg)
        if len(self.committed_messages[msg.seq_num]) >= 2 * f + 1:
            print(f"Commit result: {msg}")
            self.reply(msg)

    def reply(self, msg):
        url = 'http://'+self.node_resolve+':'+str(host_port)+'/node_reply'
        requests.post(url, json={'seq_num': msg.seq_num, 'digest': msg.digest, 'node_id': self.node_id})

    def available_node(self):
        if self.node_resolve == 'localhost':
            url = 'http://localhost:' + str(host_port) + '/next_node'
            try:
                response = requests.post(url, json={'node_id': self.node_id})
                if response.status_code == 200:
                    next_node = response.json().get('next_node')
                    return next_node
                if response.status_code == 404:
                    next_node = response.json().get('next_node')
                    return next_node
            except requests.exceptions.ConnectionError:
                return 0
        else:
            for resolve in self.node_resolve:
                url = 'http://' + resolve + ':' + str(host_port) + '/next_node'
                try:
                    response = requests.post(url, json={'node_id': self.node_id})
                    if response.status_code == 200:
                        next_node = response.json().get('next_node')
                        return next_node
                    if response.status_code == 404:
                        next_node = response.json().get('next_node')
                        return next_node
                except requests.exceptions.ConnectionError:
                    continue
            return None

    def synchronize_blockchains(self):
        last_blocks = blockchain.chain[-5:]
        last_hashes = [block.hash for block in last_blocks]
        self.send_all({'type': 'SYNC', 'hashes': last_hashes})
        responses = []
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://' + self.node_resolve + ':' + str(host_port) + '/node_sync'
                response = requests.post(url, json={'node_id': self.node_id, 'hashes': last_hashes})
                if response.status_code == 200:
                    responses.append(response.json())
        if all(response['hashes'] == last_two_hashes for response in responses):
            blockchain.save_chain()
        else:
            print("Nodes do not agree on the last two hashes.")

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
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1 per second"]
)
print(f"Welcome to {coin_name}!")
bootup(__file__, check, host_version_url, coin_name, client_port, host_port, a, b, c, e, d, reward, decimals, short_name, time_between_rewards, consensus_count, base, max_base)
print(f"Initializing {coin_name} Node...")
next_node_id = PBFTNode(0, NodeRole.PRIMARY, node_dns).available_node()
if next_node_id is not None:
    nodes = [PBFTNode(next_node_id, NodeRole.PRIMARY if next_node_id == 0 else NodeRole.REPLICA, node_dns)]
    role = "PRIMARY" if nodes[0].role == NodeRole.PRIMARY else f"REPLICA {nodes[0].node_id}"
    print(f"Node {role}\nLoading blockchain...")
else:
    print("Failed to initialize P2P node connection.")
    sys.exit(1)
blockchain = Blockchain()
difficulty, target, limit = blockchain.get_difficulty_and_target()
print(f"Blockchain initialized.\nCurrent block: {blockchain.get_latest_index()}\nNext block difficulty: {difficulty}")

@app.route('/difficulty', methods=['GET'])
@limiter.limit(f"2 per second")
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
    
@app.route('/blocks', methods=['GET'])
@limiter.limit("2 per second")
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
        print(f"Error: {e}")
        return jsonify({'error': 'Cannot get blocks.'}), 500
    
last_reward_time = time.time()
@app.route('/add_block', methods=['POST'])
@limiter.limit(f"2 per second")
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
#TODO send to other nodes for consensus
#TODO Is it malicious? Timing issue between nodes(wait/verify)?
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
                    try:
                        parsed_ip = urlparse(f"http://" + miner_ip + ":"+str(client_port))
                        if not parsed_ip.hostname or parsed_ip.hostname != miner_ip or not parsed_ip.port or parsed_ip.port != client_port:
                            print(f"Bad IP: {miner_ip}\nBad Port: {client_port}")
                            return jsonify({"message": "Invalid IP address."}), 400
                        ip = ip_address(miner_ip)
                        if local == True:
                            print(f"Local check is True, local IPs allowed.")
                        elif ip.is_private:
                            print(f"Bad IP: {miner_ip}\nBad Port: {client_port}")
                            return jsonify({"message": "Invalid IP address."}), 400
                    except ValueError as e:
                        print(f"Bad IP: {miner_ip}\nBad Port: {client_port}\nError {e}")
                        return jsonify({"message": "Invalid IP address."}), 400
                    response = requests.post(f'http://'+miner_ip+':'+str(client_port)+'/update_wallet', json=data)
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
@limiter.limit("2 per second")
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
@limiter.limit("12 per minute")
def check_client():
    data = request.get_json()
    if check == False:
        return jsonify({"message": "Host verification disabled.", "decimals": decimals}), 200
    client_hash = data.get('client_hash')
    if client_hash == client_version:
        return jsonify({"message": "Client verified!", "decimals": decimals}), 200
    else:
        return jsonify({"message": "Client verification failed."}), 400
        
@app.route('/wallet_exists', methods=['POST'])
@limiter.limit("1 per second")
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
        print(f"Error: {e}")
        return jsonify({'exists': False}), 500

@app.route('/get_wallet', methods=['POST'])
@limiter.limit("1 per second")
def get_wallet():
    data = request.get_json()
    public_key = data.get('public_key')
    trust_hash = data.get('is_trusted')
    if check == True:
        if os.path.exists('trustwallet.json'):
            with open('trustwallet.json', 'r') as f:
                trust_wallets = json.load(f)
        else:
            trust_wallets = []
        for wallet in wallets:
            if wallet['public_key'] == public_key:
                for trust_wallet in trust_wallets:
                    if trust_wallet['public_key'] == public_key and trust_wallet['is_trusted'] == trust_hash:
                        return jsonify({
                            'private_key': wallet['private_key'],
                            'public_key': wallet['public_key'],
                            'amount': float(wallet['amount'])
                        })
                return jsonify({'error': 'Trust hash mismatch.'}), 400
    else:
        with open('hostwallet.json', 'r') as f:
            wallets = json.load(f)
        for wallet in wallets:
            if wallet['public_key'] == public_key:
                return jsonify({
                    'private_key': wallet['private_key'],
                    'public_key': wallet['public_key'],
                    'amount': float(wallet['amount'])
                })
        print("Trust check disabled.")
        return jsonify({'private_key': wallet['private_key'], 'public_key': wallet['public_key'], 'amount': float(wallet['amount'])}), 200
    return jsonify({'error': 'Wallet not found.'}), 400

@app.route('/create_wallet', methods=['POST'])
@limiter.limit("1 per second")
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
            trust_hash = wallet_data.get('trust_hash')
            if trust_hash != False:
                trustwallet_path = 'trustwallet.json'
                try:
                    with open('hostwallet.json', 'r') as f:
                        wallets = json.load(f)
                except FileNotFoundError:
                    wallets = []
                    with open('hostwallet.json', 'w') as f:
                        wallet_data.pop('trust_hash', None)
                        json.dump(wallets, f, indent=4)
                if trust_hash not in [wallet['trust_hash'] for wallet in wallets]:
                    wallets.append(wallet_data)
                    wallet_data.pop('mnemonic', None)
                    wallet_data.pop('seed', None)
                    wallet_data.pop('private_key', None)
                    wallet_data.pop('coin_name', None)
                    wallet_data.pop('amount', None)
                    wallet_data.pop('nickname', None)
                    with open(trustwallet_path, 'w') as f:
                        json.dump(wallets, f, indent=4)
            if not public_key.startswith(short_name) and r_coin_name != coin_name:
                return jsonify({'exists': False, 'message': f'{public_key} is invalid.'}), 400
            wallet_data.pop('coin_name', None)
            try:
                with open('hostwallet.json', 'r') as f:
                    wallets = json.load(f)
            except FileNotFoundError:
                wallets = []
            formatted_amount = '{:.{}f}'.format(0, decimals)
            wallets.append({
                'mnemonic': mnemonic,
                'seed': seed,
                'private_key': private_key,
                'public_key': public_key,
                'nickname': nickname,
                'amount': formatted_amount
            })
            with open('hostwallet.json', 'w') as f:
                json.dump(wallets, f, indent=4)
        return jsonify({'message': f'Wallet {public_key} created!'}), 200
    else:
        print(f"Malformed wallet: mnemonic: {mnemonic}\nseed: {seed}\nprivate_key: {private_key}\npublic_key: {public_key}\nnickname: {nickname}\namount: {amount}")
        return jsonify({'error': 'Invalid data format.'}), 400

@app.route('/add_amount', methods=['POST'])
@limiter.limit(f"1 per second")
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
        print(f"Error: {e}")
        return jsonify({'message': f'Error adding {amount} to {public_key}'}), 500

@app.route('/wallet_list', methods=['GET'])
@limiter.limit("12 per minute")
def wallet_list():
    response = requests.get(wallet_list_url)
    if response.status_code == 200:
        wordlist = response.text.splitlines()
        entropy = secrets.token_bytes(128 // 8)
        mnemonic = entropy_to_mnemonic(entropy, wordlist)
        return jsonify({'mnemonic': mnemonic}), 200
    else:
        print(f"Response: {response}")
        return jsonify({'error': 'Failed to fetch wordlist.'}), 500

@app.route('/node_receive', methods=['POST'])
def receive_message():
    msg = request.get_json()
    node_id = int(request.args.get('node_id'))
    if not nodes[node_id].reached_correct_consensus():
        print(f"Malicious node {node_id} detected: {msg}")
        return jsonify({'status': 'Error', 'message': 'Malicious node detected'}), 400
    nodes[node_id].receive_message(msg)
    return jsonify({'status': 'Success'}), 200

@app.route('/node_reply', methods=['POST'])
def reply():
    data = request.get_json()
    seq_num = data['seq_num']
    digest = data['digest']
    node_id = data['node_id']
    if not nodes[node_id].reached_correct_consensus():
        print(f"Malicious node {node_id} failed seq_num {seq_num} with digest {digest}")
        return jsonify({'status': 'Error', 'message': 'Malicious node detected'}), 400
    print(f"Node {node_id} reached consensus on seq_num {seq_num} with digest {digest}")
    return jsonify({'status': 'Success'}), 200

@app.route('/node_request', methods=['POST'])
def client_request():
    request_data = request.get_json()
    request_str = json.dumps(request_data)
    if not nodes[0].reached_correct_consensus():
        print(f"Malicious node detected. {request_str}")
        return jsonify({'status': 'Error', 'message': 'Malicious node detected'}), 400
    nodes[0].pre_prepare(request_str)
    return jsonify({'status': 'Request sent to primary'}), 200

next_node_val = 0
@app.route('/next_node', methods=['POST'])
def next_node():
    global next_node_val
    data = request.get_json()
    available_nodes = data.get('node_id')
    time.sleep(1)
    #TODO Almost implimented, available_nodes doesnt consolidate
    if available_nodes == 0 and next_node_val == 0:
        next_node_val = 1
        print(f"Starting first REPLICA node {next_node_val}")
        return jsonify({'next_node': int(next_node_val)}), 200
    else:
        next_node_val += 1
        print(f"Starting REPLICA node {next_node_val}")
        return jsonify({'next_node': int(next_node_val)}), 200

@app.route('/node_sync', methods=['POST'])
def node_sync():
    data = request.json
    node_id = data['node_id']
    received_hashes = data['hashes']
    last_blocks = blockchain.chain[-5:]
    last_hashes = [block.hash for block in last_blocks]
    if received_hashes == last_two_hashes:
        return jsonify({'status': 'success', 'hashes': last_hashes}), 200
    else:
        return jsonify({'status': 'failure', 'hashes': last_hashes}), 400

if __name__ == '__main__':
    print(f"{coin_name} Node Initialized.")
    app.run(port=host_port)
