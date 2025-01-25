# Author: dotslashCosmic v0.1.2
import hashlib, time, json, requests, os, sys, math, secrets
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from collections import defaultdict
from ipaddress import ip_address
from urllib.parse import urlparse
from enum import Enum

#TODO bootup the new get difficulty vars

coin_name = "zQoin" #Coin full name
short_name = "zqn" #Coin short name(lowercase/numbers, up to 5 chars)
client_port = 5317 #int 1-65535
host_port = 5318 #int 1-65535
base = 64 #Base difficulty
max_base = 1024 #Maximum difficulty
logarithmic = float(5) # Float 0-10, +log growth
linear = float(4) # Float 0-10, +linear growth
ramp_factor = 0.77 # Float 0-1, lower for slower difficulty ramp-up speed
max_coin = 7777777777 #Maximum amount of coins in circulation, ~462mb per 1m max_coin/reward, ~580 bytes per wallet, ~260 bytes per trust wallet
reward = 100.0000000 #Base coin reward, float
winner_percent = 50.0 #How much in percent the winner gets of the reward, 0-100, float
decimals = 8 #Maximum trailing decimals for reward, int 0-8, absolute limit of 8
time_between_rewards = 10 #Minimum seconds between blocks, int
consensus_count = 1 #Minimum verifications for consensus per node
node_consensus = 1 #Minimum nodes for consensus verification
node_tolerance = 0 #Tolerance for faulty nodes
wallet_list_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/wordlist/en.txt" #Wallet creation word list
host_version_url = "https://raw.githubusercontent.com/dotslashCosmic/zQoinPython/main/hash/host.sha3_512" #SHA3-512 of this file
check = False #Bool, validate host/client with host_version_url/client_version
local = True #Bool, allows local IPs
node_dns = 'localhost' # DNS resolve to nodes list, in progress
client_version = "b12bee9a69ac0ff8a0ed4ae134b7009d4674713244f3e455224182dac33a494d1b4857217fc5b51da5c4d95c473471203bbf4d918ee958b606be9c916458270d" #SHA3-512 of client.py
genesis_token = f'{client_version}{host_version_url}{coin_name}GENESIS' #Genesis block
consensus_results = defaultdict(list) #Initialize

def bootup(__file__, check, host_version_url, coin_name, client_port, host_port, logarithmic, linear, ramp_factor, reward, decimals, short_name, time_between_rewards, consensus_count, base, max_base):
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
    if not isinstance(logarithmic, float) or logarithmic < 0:
        print(f"'logarithmic' must be a float and at least 0. Current value: {logarithmic}")
        sys.exit(1)
    if not isinstance(linear, float) or linear < 0:
        print(f"'linear' must be a float and at least 0. Current value: {linear}")
        sys.exit(1)
    if not isinstance(ramp_factor, float) or ramp_factor < 0:
        print(f"'ramp_factor' must be a float and at least 0. Current value: {ramp_factor}")
        sys.exit(1)
    if not isinstance(node_consensus, int) or node_consensus < 0:
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
    #check to make sure winner_percent is 0-100, no negative, float
    if not isinstance(winner_percent, float) or winner_percent < 0 or winner_percent > 100:
        print(f"'winner_percent' must be a float between 0 and 100.")
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
    if base > 64:
        print(f"Warning! 'base' is very large to start ({base}).")
    if not isinstance(max_base, int) or max_base < 1:
        print(f"'max_base' must be an integer and at least 1. Current value: {max_base}")
        sys.exit(1)
    if max_base > 512:
        print(f"Warning: 'max_base' is very large ({max_base}).")
    next_node_id = PBFT(0, Role.NODE, node_dns).available_node()
    if next_node_id is not None:
        nodes = [PBFT(next_node_id, Role.NODE if next_node_id == 0 else Role.NODE, node_dns)]
        role = 1 if nodes[0].role == Role.NODE else f"NODE {nodes[0].node_id}"
        print(f"Node {role}")
    else:
        print("Failed to initialize P2P node connection.")
        sys.exit(1)

def create_genesis_block():
    index = 0
    timestamp = int(time.time())
    nonce = int.from_bytes(os.urandom(8), 'big')
    genesis = hashlib.sha3_512((str(timestamp)+str(nonce)+genesis_token).encode()).hexdigest()
    hash_ = hashlib.sha3_512((str(index)+str(timestamp)+str(nonce)).encode('utf-8')).hexdigest()
    request = json.dumps({
        'i': index,
        't': timestamp,
        'g': genesis,
        'n': nonce
    })
    return Block(index, timestamp, genesis, nonce)

class Role(Enum):
    NODE = 1

class Type(Enum):
    PRE_PREPARE = 1
    PREPARE = 2
    COMMIT = 3
    REPLY = 4

class Msg:
    def __init__(self, msg_type, view, seq_num, digest, node_id):
        self.msg_type = msg_type
        self.view = view
        self.seq_num = seq_num
        self.digest = digest
        self.node_id = node_id

class PBFT:
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
                self.alert_faulty(seq_num)
                self.committed_messages[seq_num] = [msg for msg in messages if msg.digest == digests[0]]
                return False
        #TODO Allow save the blockchain here, then wait/make sure all blockchains are saved before continuing, verify with the rest, and then allow the next block to be available
        print("Nodes have agreed on consensus.")
        blockchain.chain.append(new_block)
        self.synchronize_blockchains()
        return True

    def alert_faulty(self, seq_num):
        digests = [msg.digest for msg in self.committed_messages[seq_num]]
        faulty_digest = max(set(digests), key=digests.count)
        faulty_nodes = [msg.node_id for msg in self.committed_messages[seq_num] if msg.digest != faulty_digest]
        alert_msg = {'seq_num': seq_num, 'message': 'Faulty node detected', 'faulty_nodes': faulty_nodes}
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://'+self.node_resolve+':'+str(host_port)+'/node_alert'
                print(f"ALERT! {alert_msg}")
                requests.post(url, json=alert_msg)
        
    def send_all(self, msg):
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://'+self.node_resolve+':'+str(host_port)+'/node_receive'
                requests.post(url, json=msg.__dict__)

    def receive_message(self, msg):
        msg = Msg(**msg)
        if msg.msg_type == Type.PRE_PREPARE:
            self.prepare(msg)
        elif msg.msg_type == Type.PREPARE:
            self.commit(msg)
        elif msg.msg_type == Type.COMMIT:
            self.reply(msg)

    def pre_prepare(self, request):
        if self.role == Role.NODE:
            self.seq_num += 1
            digest = hashlib.sha3_512(request.encode()).hexdigest()
            msg = Msg(Type.PRE_PREPARE, self.view, self.seq_num, digest, self.node_id)
            self.message_log.append(msg)
            print(f"Pre-prepare result: {msg}")
            self.send_all(msg)

    def prepare(self, msg):
        if self.role == Role.NODE:
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
        last_hashes = [block.hash_ for block in last_blocks]
        self.send_all({'type': 'SYNC', 'hashes': last_hashes})
        responses = []
        for node in nodes:
            if node.node_id != self.node_id:
                url = 'http://' + self.node_resolve + ':' + str(host_port) + '/node_sync'
                response = requests.post(url, json={'node_id': self.node_id, 'hashes': last_hashes})
                if response.status_code == 200:
                    responses.append(response.json())
        if all(response['hashes'] == last_hashes for response in responses):
            blockchain.save_chain()
        else:
            print("Nodes do not agree on the last two hashes.")

class Block:
    def __init__(self, index, timestamp, data, nonce):
        self.index = index
        cur_index = self.index
        self.timestamp = timestamp
        self.data = data
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
                        "i": block.index,
                        "t": block.timestamp,
                        "d": block.data,
                        "n": block.nonce,
                    }
                    chain_data.append(block_data)
                    seen_indexes.add(block.index)
            json.dump({'chain': chain_data, 'balances': self.balances}, f)

    def load_chain(self):
        try:
            with open('blockchain.json', 'r') as f:
                data = json.load(f)
                self.chain = [Block(
                    block['i'],
                    block['t'],
                    block.get('d'),
                    block['n'],
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
            
    def get_difficulty_and_target(self):
        global max_base
        if self.chain:
            index = self.chain[-1].index
        else:
            index = 0
        difficulty = int(((math.log(index + base) - 1 * logarithmic) + (index * linear/max_coin)) * ramp_factor) + base
        difficulty = max(difficulty, base)
        hex_target = ''.join(format(ord(char), '02x') for char in short_name)
        target = (hex_target * (difficulty // len(hex_target) + 1))[:difficulty]
        if index >= max_coin or difficulty >= max_base:
            difficulty = max_base
            target = short_name * ((max_base // len(short_name)) + 1)
            limit = True
            return difficulty, target, limit
        limit = False
        return difficulty, target, limit

    def get_latest_block(self):
        return self.chain[-1]

    def get_latest_index(self):
        return self.get_latest_block().index
    
    def get_latest_hash(self):
        return self.get_latest_block().data
        
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
print("Initializing blockchain...")
blockchain = Blockchain()
difficulty, target, limit = blockchain.get_difficulty_and_target()
print(f"Current block: {blockchain.get_latest_index()}\nBlock difficulty: {difficulty}")
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
            if block.hash_ not in seen_hashes:
                chain_data.append({
                    "i": block.index,
                    "t": block.timestamp,
                    "h": block.hash_
                })
                seen_hashes.add(block.hash_)
        return jsonify(chain_data), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Cannot get blocks.'}), 500

@app.route('/latest_block', methods=['GET'])
@limiter.limit("2 per second")
def latest_block():
    latest_block = blockchain.get_latest_block()
    #get the newest 'd' in the blockchain according to the 't' timestamp
    block_data = {
        "i": latest_block.index,
        "t": latest_block.timestamp,
        "d": latest_block.data,
        "h": blockchain.get_latest_hash(),
        "n": latest_block.nonce,
    }
    return jsonify(block_data), 200

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
        print("Block data, find the new nonce ", block_data)
        if 'last_hashes' in block_data:
            data = block_data['last_hashes']
        else:
            data = []  # or handle it as needed for the first block
        if 'nonce' in block_data:
            nonce = block_data['nonce']
        else:
            nonce = []  # or handle it as needed for the first block
        if 'new_hash' in block_data:
            new_hash = block_data['new_hash']
        else:
            new_hash = []  # or handle it as needed for the first block
        if 'miner' in block_data and isinstance(block_data['miner'], str):
            miner = block_data['miner']
        else:
            return jsonify({"message": "Invalid or missing miner."}), 400
        if data:
            first_hash = data.split('[')[0]
        else:
            first_hash = ""
        previous_block = blockchain.get_latest_block()
        index = previous_block.index + 1
        timestamp = int(time.time())
        result = {
        'nonce': nonce,
        'new_hash': new_hash,
        'first_hash': first_hash}
        if index not in consensus_results:
            consensus_results[index] = {}
        if miner not in consensus_results[index]:
            consensus_results[index][miner] = result
        else:
            return jsonify({"message": f"Miner {miner} has already verified consensus block {index}"}), 400
        matching_results = []
        print(f"Consensus {len(matching_results)+1}/{consensus_count} for block {index} from miner {miner}")
        while time.time() - last_reward_time < time_between_rewards:
            time.sleep(0.001)
        for block_index, block_consensus in consensus_results.items():
            if block_index == index:
                for address, result in block_consensus.items():
                    matching_results.append(result)
        if len(matching_results) >= consensus_count:
            if time.time() - last_reward_time >= time_between_rewards:
                if not nonce:
                    nonce = 1
                data_hash = hashlib.sha3_512(''.join(data).encode('utf-8')).hexdigest()
                new_hash = block_data['d']
                #apply vars new_hash and new_nonce in the chain to be 'd' and 'n'
                if limit == True:
                    winner_reward = float(0)
                    miner_reward = float(0)
                elif limit == False:
                    miner_reward = float((reward * (1 - (winner_percent / 100))) / consensus_count)
                    winner_reward = float(reward * (winner_percent / 100))
                    winning_wallet = block_data['miner']
                print(f"Block {index} mined: {new_hash}\nReward for each of {consensus_count} miners: {miner_reward:.{decimals}f} {coin_name}\nBonus for winner {winner_reward:.{decimals}f} {coin_name}")
                for address, result in consensus_results[index].items():
# properly send winner_reward to the winner instead of a standard miner_reward share, or add the bonus to just winner
#                    updatewinner = {
#                        'message': "approved",
#                        'address': winning_wallet,
#                        'decimals': decimals,
#                        'amount': winner_reward
#                    }
                    update = {
                        'message': "approved",
                        'address': address,
                        'decimals': decimals,
                        'amount': float(f"{miner_reward:.{decimals}f}")
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
                            response = requests.post(f'http://' + miner_ip + ':'+str(client_port)+'/update_wallet', json=update)
                        elif ip.is_private:
                            print(f"Bad IP: {miner_ip}\nBad Port: {client_port}")
                            return jsonify({"message": "Invalid IP address."}), 400
                        else:
                            response = requests.post(f'http://' + miner_ip + ':'+str(client_port)+'/update_wallet', json=update)
                    except ValueError as e:
                        print(f"Bad IP: {miner_ip}\nBad Port: {client_port}\nError {e}")
                        return jsonify({"message": "Invalid IP address."}), 400
                    print(f"Sent {miner_reward} to {address}, response status: {response.status_code}")
                    if response.status_code == 200:
                        with open('hostwallet.json', 'r') as f:
                            host_wallets = json.load(f)
                        for wallet in host_wallets:
                            if wallet['public_key'] == address:
                                wallet['amount'] = float(wallet['amount']) + float(miner_reward)
                                wallet['amount'] = f"{wallet['amount']:.{decimals}f}"
                                break
                        with open('hostwallet.json', 'w') as f:
                            json.dump(host_wallets, f, indent=4)
                new_block = Block(index, timestamp, new_hash, nonce)
                new_block.nonce = nonce
                new_block.new_hash = new_hash
                blockchain.chain.append(new_block)
                blockchain.save_chain()
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
    
@app.route('/check_client', methods=['POST'])
@limiter.limit("1 per second")
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
    trust_hash = data.get('trust_hash')
    if check == True:
        if os.path.exists('trustwallet.json'):
            with open('trustwallet.json', 'r') as f:
                trust_wallets = json.load(f)
        else:
            trust_wallets = []
        for wallet in wallets:
            if wallet['public_key'] == public_key:
                for trust_wallet in trust_wallets:
                    if trust_wallet['public_key'] == public_key and trust_wallet['trust_hash'] == trust_hash:
                        return jsonify({
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
                    'public_key': wallet['public_key'],
                    'amount': float(wallet['amount'])
                })
        print("Trust check disabled.")
        return jsonify({'public_key': wallet['public_key'], 'amount': float(wallet['amount'])}), 200
    return jsonify({'error': 'Wallet not found.'}), 400

@app.route('/create_wallet', methods=['POST'])
@limiter.limit("1 per second")
def create_wallet():
    data = request.get_json()
    if isinstance(data, list):
        for wallet_data in data:
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
                'public_key': public_key,
                'nickname': nickname,
                'amount': formatted_amount
            })
            with open('hostwallet.json', 'w') as f:
                json.dump(wallets, f, indent=4)
        return jsonify({'message': f'Wallet {public_key} created!'}), 200
    else:
        print(f"Malformed wallet: Public_key: {public_key}\nnickname: {nickname}\namount: {formatted_amount}")
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
@limiter.limit("1 per second")
def wallet_list():
    response = requests.get(wallet_list_url)
    if response.status_code == 200:
        return wallet_list_url, 200
    else:
        print(f"Response: {response}")
        return jsonify({'w': 'Failed to fetch wallet list.'}), 500

@app.route('/node_receive', methods=['POST'])
def receive_message():
    msg = request.get_json()
    node_id = int(request.args.get('node_id'))
    if not nodes[node_id].reached_correct_consensus():
        print(f"Faulty node {node_id} detected: {msg}")
        return jsonify({'status': 'Error', 'message': 'Faulty node detected.'}), 400
    nodes[node_id].receive_message(msg)
    return jsonify({'status': 'Success'}), 200

@app.route('/node_reply', methods=['POST'])
def reply():
    data = request.get_json()
    seq_num = data['seq_num']
    digest = data['digest']
    node_id = data['node_id']
    if not nodes[node_id].reached_correct_consensus():
        print(f"Faulty node {node_id} failed seq_num {seq_num} with digest {digest}")
        return jsonify({'status': 'Error', 'message': 'Faulty node detected.'}), 400
    print(f"Node {node_id} reached consensus on seq_num {seq_num} with digest {digest}")
    return jsonify({'status': 'Success'}), 200

@app.route('/node_request', methods=['POST'])
def client_request():
    request_data = request.get_json()
    request_str = json.dumps(request_data)
    if not nodes[0].reached_correct_consensus():
        print(f"Faulty node detected. {request_str}")
        return jsonify({'status': 'Error', 'message': 'Faulty node detected.'}), 400
    nodes[0].pre_prepare(request_str)
    return jsonify({'status': 'Request sent to consensus.'}), 200

next_node_val = 0
@app.route('/next_node', methods=['POST'])
def next_node():
    global next_node_val
    data = request.get_json()
    available_nodes = data.get('node_id')
    time.sleep(1)
    #TODO Almost implimented, available_nodes doesnt consolidate
    #among what, across connections of node_dns?
    if available_nodes == 0 and next_node_val == 0:
        next_node_val = 1
        print(f"Starting first NODE node {next_node_val}")
        return jsonify({'next_node': int(next_node_val)}), 200
    else:
        next_node_val += 1
        print(f"Starting NODE node {next_node_val}")
        return jsonify({'next_node': int(next_node_val)}), 200

@app.route('/node_sync', methods=['POST'])
def node_sync():
    data = request.json
    node_id = data['node_id']
    received_hashes = data['hashes']
    last_blocks = blockchain.chain[-5:]
    last_hashes = [block.hash_ for block in last_blocks]
    if received_hashes == last_hashes:
        return jsonify({'status': 'success', 'hashes': last_hashes}), 200
    else:
        return jsonify({'status': 'failure', 'hashes': last_hashes}), 400

if __name__ == '__main__':
    bootup(__file__, check, host_version_url, coin_name, client_port, host_port, logarithmic, linear, ramp_factor, reward, decimals, short_name, time_between_rewards, consensus_count, base, max_base)
    print(f"{coin_name} node initialized!")
    app.run(port=host_port)
