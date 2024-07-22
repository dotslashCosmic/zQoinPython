import hashlib, time, json
from flask import Flask, jsonify, request
from client import BlockchainGUI 

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
    index = 0
    previous_hash = "0"
    timestamp = int(time.time())
    data = "GENESISzQoinGENESIS"
    nonce = 53100
    hash = calculate_hash(index, previous_hash, timestamp, data, nonce)
    return Block(index, previous_hash, timestamp, data, hash, nonce)

class Blockchain:
    def __init__(self):
        self.chain = []
        self.balances = {}
        self.difficulty, self.target, self.max_base = self.get_difficulty_and_target()
        self.load_chain()
        self.transaction_pool = []

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
            print("Blockchain index:", index)
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

    def proof_of_work(self, index, previous_hash, timestamp, data):
        nonce = 53100
        difficulty, _ = self.get_difficulty_and_target()
        while True:
            hash = calculate_hash(index, previous_hash, timestamp, data, nonce)
            if hash[:difficulty] == '0' * difficulty:
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
print("Blockchain initialized.\nNext block difficulty:", difficulty, "\nInitializing zQoin Node...")

@app.route('/difficulty', methods=['GET'])
def get_difficulty():
    difficulty, target, max_base = blockchain.get_difficulty_and_target()
    if difficulty >= max_base:
        print(f"Reached the maximum limit of {index} zQoin in circulation.")
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
    block_data = request.json
    print("Received block data:", block_data)
    data = block_data['data']
    hash = block_data['hash']
    hash_rate = block_data['hash_rate']
    previous_block = blockchain.get_latest_block()
    index = previous_block.index + 1
    timestamp = int(time.time())
    previous_hash = previous_block.hash
    nonce = 53100
    new_block = Block(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest(), hash, nonce)
    blockchain.chain.append(new_block)
    blockchain.save_chain()
    return jsonify({"message": "Block added successfully!"})

if __name__ == '__main__':
    print("zQoin Node Initialized.")
    app.run(port=5310)
