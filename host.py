import hashlib, time, json
from flask import Flask, jsonify, request

class Block:
    def __init__(self, index, previous_hash, timestamp, data, hash):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash

def calculate_hash(index, previous_hash, timestamp, data):
    value = str(index) + str(previous_hash) + str(timestamp) + str(data)
    return hashlib.sha3_512(value.encode('utf-8')).hexdigest()

def create_genesis_block():
    index = 0
    previous_hash = "0"
    timestamp = int(time.time())
    data = "zQoin"
    hash = calculate_hash(index, previous_hash, timestamp, data)
    return Block(index, previous_hash, timestamp, data, hash)

class Blockchain:
    def __init__(self):
        self.chain = []
        self.balances = {}
        self.load_chain()

    def save_chain(self):

        with open('blockchain.json', 'w') as f:
            chain_data = []
            seen_indexes = set()
            for block in self.chain:
                if block.index not in seen_indexes:
                    block_data = {
                        "index": block.index,
                        "timestamp": block.timestamp,
                        "hash": block.hash
                    }
                    chain_data.append(block_data)
                    seen_indexes.add(block.index)
            json.dump({'chain': chain_data, 'balances': self.balances}, f)

    def load_chain(self):
        try:
            with open('blockchain.json', 'r') as f:
                data = json.load(f)
                self.chain = [Block(**block) for block in data['chain']]
                self.balances = data['balances']
        except FileNotFoundError:
            self.chain.append(create_genesis_block())
            self.balances["0"] = 0

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, transaction, miner_address):
        previous_block = self.get_latest_block()
        index = previous_block.index + 1
        timestamp = int(time.time())
        previous_hash = previous_block.hash
        data = transaction
        hash = calculate_hash(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest())
        new_block = Block(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest(), hash)
        self.chain.append(new_block)
        self.update_balances(transaction, miner_address)
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
blockchain = Blockchain()
@app.route('/blocks', methods=['GET'])
def get_blocks():
    chain_data = []
    seen_hashes = set()
    for block in blockchain.chain:
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
    new_block = Block(index, previous_hash, timestamp, hashlib.sha3_512(data.encode('utf-8')).hexdigest(), hash)
    blockchain.chain.append(new_block)
    blockchain.save_chain()
    return jsonify({"message": "Block added successfully!"})

if __name__ == '__main__':
    app.run(port=5000)
