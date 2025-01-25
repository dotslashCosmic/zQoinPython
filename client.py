#Author: dotslashCosmic v0.1.2
import threading, time, requests, json, hashlib, os, binascii, secrets, sys, uuid, random
import tkinter as tk
from flask import Flask, request, jsonify
from tkinter import simpledialog
from tkinter import messagebox
from datetime import datetime

client_port = 5317 #int, 1-65535
host_port = 5318 #int, 1-65535
node_dns = f'http://127.0.0.1:{host_port}' #Node_dns, future update
coin_name = 'zQoin' #Coin full name
short_name = 'zqn' #Coin short name(lowercase/numbers)

for port, p_name in [(client_port, "Client"), (host_port, "Host")]:
    if not isinstance(port, int) or not (1 <= port <= 65535):
        print(f"{p_name} port {port} is not a valid port number. It must be an integer between 1 and 65535.")
        sys.exit(1)
if client_port == host_port:
    print(f"Client port {client_port} and host port {host_port} cannot be the same.")
if not (1 <= len(short_name) <= 5 and all(char.islower() or char.isdigit() for char in short_name)):
    print("Short name must be between 1 and 5 characters and only contain lowercase letters and digits.")
    sys.exit(1)

def entropy_to_mnemonic(entropy, wordlist):
    entropy_bits = bin(int.from_bytes(entropy, byteorder='big'))[2:].zfill(len(entropy) * 8)
    timestamp = int(time.time())
    timestamp_bytes = timestamp.to_bytes((timestamp.bit_length() + 7) // 8, byteorder='big')
    timestamp_bits = bin(int.from_bytes(timestamp_bytes, byteorder='big'))[2:].zfill(len(timestamp_bytes) * 8)
    rng = int(random.getrandbits(128))
    rng_bytes = rng.to_bytes((rng.bit_length() + 7) // 8, byteorder='big')
    rng_bits = bin(int.from_bytes(rng_bytes, byteorder='big'))[2:].zfill(len(rng_bytes) * 8)
    combined = entropy + timestamp_bytes + rng_bytes
    checksum = bin(int(hashlib.sha3_512(combined).hexdigest(), 16))[2:].zfill(512)[:(len(entropy_bits) // 32)]
    bits = entropy_bits + checksum + timestamp_bits + rng_bits
    words = [wordlist[int(bits[i:i+11], 2)] for i in range(0, len(bits), 11)]
    return ' '.join(words)

class Wallet:
    #Only allows 1 wallet per computer
    def __init__(self, nickname, amount=0):
        self.mnemonic = self.fetch_mnemonic()
        self.seed = hashlib.pbkdf2_hmac('sha3_512', self.mnemonic.encode(), (coin_name.encode() + nickname.encode()), 2048, dklen=64)
        self.private_key = self.generate_private_key(self.seed)
        self.public_key = self.generate_public_key(self.private_key)
        self.trust = self.trust_hash()
        self.nickname = nickname
        self.amount = amount
        
    def trust_hash(self):
        trust = hashlib.sha3_512((str(uuid.uuid1()) + self.public_key).encode()).hexdigest()
        return trust
    
    def fetch_mnemonic(self):
        list_url = node_dns + '/wallet_list'
        response = requests.get(list_url)
        url = response.text.splitlines()[0]
        second_response = requests.get(url)
        second_response_lines = second_response.text.splitlines()
        entropy = secrets.token_bytes(256 // 8)
        mnemonic = entropy_to_mnemonic(entropy, second_response_lines)
        return mnemonic

    def generate_private_key(self, seed):
        return hashlib.sha3_512(seed).hexdigest()

    def generate_public_key(self, private_key):
        hash_length = 64 - len(short_name)
        return short_name + hashlib.sha3_512(private_key.encode('utf-8')).hexdigest()[-hash_length:]

    def save_keys(self):
        response = requests.post(node_dns+'/wallet_exists', json={'public_key': self.public_key})
        f_amount = '{:.{}f}'.format(0, decimals)
        if not response.json().get('exists'):
            wallet_data = {
                'mnemonic': self.mnemonic,
                'seed': binascii.hexlify(self.seed).decode(),
                'private_key': self.private_key,
                'public_key': self.public_key,
                'nickname': self.nickname,
                'coin_name': coin_name,
                'trust_hash': self.trust,
                'amount': f_amount
            }
            trust = tk.Tk()
            trust.withdraw()
            result = messagebox.askyesno("Trust This Device", f"Do you want to save this computer as a trusted source for:\nWallet Nickname: {self.nickname}\nPublic Wallet Address: {self.public_key}?")
            if result:
                wallet_data['trust_hash'] = self.trust
            else:
                wallet_data['trust_hash'] = False
            print(f"WRITE YOUR RECOVERY CODE DOWN!\nThis will only show once!\n\n{self.mnemonic}\n")
            response = requests.post(node_dns+'/create_wallet', json=[wallet_data])
            if response.status_code == 200:
                wallet_data.pop('coin_name', None)
                with open('wallet.json', 'w') as f:
                    json.dump([wallet_data], f, indent=4)
            else:
                print("Wallet creation failed.")
                return

    def load_keys(self):
        is_trusted = self.trust()
        response = requests.post(node_dns+'/get_wallet', json={'public_key': self.public_key, 'trust_hash': is_trusted})
        if response.status_code == 200:
            keys = response.json()
            self.private_key = keys['private_key']
            self.public_key = keys['public_key']
            self.amount = keys['amount']
            if os.path.exists('wallet.json'):
                with open('wallet.json', 'r') as f:
                    local_keys = json.load(f)[0]
                if (self.private_key == local_keys['private_key'] and
                    self.public_key == local_keys['public_key'] and
                    self.amount == local_keys['amount']):
                    print("Wallets verified.")
                else:
                    print("Wallets verification FAILED.")
            else:
                print("Your wallet does not exist!\nTry to recover your wallet.")
        else:
            print("Failed to load keys from the server.")


def get_index():
    response = requests.get(node_dns+'/index')
    if response.status_code == 200:
        data = response.json()
        index = data['index']
    else:
        print(f"{coin_name} Node offline.")

class BlockchainGUI:
    def __init__(self, root):
        with open(__file__, 'rb') as file:
            client = file.read()
        self.client_hash = hashlib.sha3_512(client).hexdigest()
        self.check_hash_with_server()
        self.root = root
        self.root.title(f"{coin_name} GUI")
        self.mining = False
        self.hash_rate = 0
        self.wallet = None
        if os.path.exists('wallet.json'):
            with open('wallet.json', 'r') as f:
                keys = json.load(f)[0]
            self.wallet = Wallet(keys['nickname'], keys['amount'])
            self.wallet.private_key = keys['private_key']
            self.wallet.public_key = keys['public_key']
            response = requests.post(node_dns+'/get_wallet', json={'public_key': self.wallet.public_key})
            response_keys = response.json()
            if not (self.wallet.public_key == response_keys['public_key']):
                return print("Fake/non-existent wallet.")
        else:
            nickname = tk.simpledialog.askstring("Input", "Enter a nickname for the wallet:")
            if not nickname:
                messagebox.showerror("Input Error", "Nickname is required.")
                return
            self.wallet = Wallet(nickname)
            self.wallet.save_keys()
        self.sender_wallet_label = tk.Label(root, text=f"Welcome to {coin_name} Client\nCurrent Wallet: {self.wallet.nickname}\nAmount: {self.wallet.amount} {coin_name}\n\t\t\t\t\t\t")
        self.sender_wallet_label.pack(pady=10)
        self.sender_wallet_entry = tk.Entry(root)
        self.sender_wallet_entry.pack(pady=10)
        self.sender_wallet_entry.insert(0, self.wallet.public_key)
        self.sender_wallet_entry.config(state='readonly')
        self.new_wallet_button = tk.Button(root, text="Create New Wallet", command=self.create_new_wallet)
        self.new_wallet_button.pack(pady=10)
        self.mine_button = tk.Button(root, text="Mine", command=self.start_mining)
        self.mine_button.pack(pady=10)
        self.hash_rate_label = tk.Label(root, text="Hash Rate: 0 H/s")
        self.hash_rate_label.pack(pady=10)
        self.update_hash_rate()

    def check_hash_with_server(self):
        global decimals
        self.attempts = 0
        print(f"Verifying client: {self.client_hash}")
        while self.attempts < 3: #Allow up to 3 attempts
            try:
                data = {
                    'client_hash': self.client_hash
                }
                response = requests.post(node_dns+'/check_client', json=data)
                if response.status_code == 200:
                    response_json = response.json()
                    print("Client verified!")
                    if 'decimals' in response_json:
                        decimals = response_json['decimals']
                        return decimals
                    else:
                        print("Malformed packet.")
                        sys.exit(1)
                else:
                    print("Failure to verify client.")
                    sys.exit(1)
            except requests.exceptions.ConnectionError:
                self.attempts += 1
                print(f"Attempt {self.attempts} of 3 failed due to connection error.")
        print("Max retries exceeded. Unable to connect to the server.")
        sys.exit(1)

    def create_new_wallet(self):
        nickname = tk.simpledialog.askstring("Input", "Enter a nickname for the wallet:")
        if not nickname:
            messagebox.showerror("Input Error", "Nickname is required.")
            return
        self.wallet = Wallet(nickname)
        self.wallet.save_keys()
        self.sender_wallet_label.config(text=f"Welcome to {coin_name} Client\nCurrent Wallet: {self.wallet.nickname}\nAmount: {self.wallet.amount} {coin_name}\n\t\t\t\t\t\t")

    def start_mining(self):
        self.mining = True
        self.mine_button.config(text="---Stop Mining---", command=self.stop_mining)
        print("Mining starting...")
        #more power to the thread for more speed?
        threading.Thread(target=self.mine).start()
        
    def stop_mining(self):
        self.mining = False
        print("Mining stopped.")
        self.mine_button.config(text="Mine", command=self.start_mining)

    def mine(self):
        while self.mining:
            response = requests.get(node_dns+'/difficulty')
            if response.status_code == 200:
                difficulty_response = response.json()
                difficulty = difficulty_response['difficulty']
                target = difficulty_response['target']
                transactions = difficulty_response['transactions']
                nonce = difficulty_response['nonce']
                limit = difficulty_response['limit']
                if limit == True:
                    print(f"End of block rewards.")
                if not isinstance(nonce, int):
                    nonce = int(nonce[0])
            else:
                print("Failed to fetch difficulty.")
                self.stop_mining()
                return
            response = requests.get(node_dns+"/latest_block")
            if response.status_code == 200:
                blocks = response.json()
                previous_block = blocks['d']
#Data has the nonce added and nonce returns [1], fix
                previous_index = blocks['i']
                previous_hash = blocks['h']
            else:
                print("Failed to fetch the latest block.")
                self.stop_mining()
                return
            new_index = previous_index + 1
            start_time = int(time.time())
            form_time = datetime.fromtimestamp(int(start_time)).strftime('%m/%d/%Y %H:%M:%S')
            print(f"PoW for block {new_index} at difficulty {difficulty} starting at {form_time}...")
            nonce, new_hash = self.proof_of_work(previous_hash, start_time, transactions, nonce, difficulty, target)
            end_time = time.time()
            time_diff = end_time - start_time
            print(f"Time to mine block {new_index}: {time_diff:.2f}s")
            if time_diff == 0:
                self.hash_rate = float('inf')
            else:
                self.hash_rate = 1 / time_diff
            block_data = {
                'd': new_hash,
                'miner': self.wallet.public_key,
                'nonce': nonce
            }
            #TODO the nonce isnt being displayed on blockchain.json correctly- its [1] instead of an int of the nonce
            #PoWMiner correctly returns as var nonce
            if '[' in block_data['d']:
                first_hash = block_data['d'].split('[')[0].strip()
                data_part = block_data['d'].split('[')[1].strip(']')
                hashes = [hash.strip().strip('"') for hash in data_part.split(',')]
                last_hashes = first_hash + str(hashes[-2:])
                block_data = {
                    'last_hashes': last_hashes,
                    'nonce': nonce,
                    'new_hash': new_hash,
                    'hash_rate': self.hash_rate,
                    'miner': self.wallet.public_key
                }
            print("Waiting for consensus...")
            response = requests.post(node_dns+'/add_block', json=block_data)
            if response.status_code == 200:
                block_time = datetime.fromtimestamp(int(end_time)).strftime('%m/%d/%Y %H:%M:%S')
                print(f"Block {new_index} mined at {block_time}!\nMined data: {new_hash}")
            else:
                message = response.json().get('message')
                if message == "Block flooding detected.":
                    print("Block flooding detected.")
                    self.stop_mining()
                elif message == "Consensus not reached yet.":
                    print("Block sent, waiting for consensus.")
                elif message == "Block declined due to connection error.":
                    print("Block declined due to connection error.")
                    self.stop_mining()
                else:
                    print("Failed to add block to the blockchain.")
                    self.stop_mining()
#New PoW
#Gpu.py

#TODO Starting transaction, merkle
    def proof_of_work(self, previous_hash, start_time, transactions, nonce, difficulty, target):
        merkle = self.merkle_tree(transactions)
        while True:
            header = merkle + str(start_time) + str(nonce)
            hash = hashlib.sha3_512(f"{header}{previous_hash}".encode('utf-8')).hexdigest()
            if hash[:difficulty] <= target:
                return nonce, hash
            nonce += 1

    def merkle_tree(self, transactions):
        if len(transactions) == 0:
            return None
        leaf_nodes = [hashlib.sha3_512(tx.encode('utf-8')) for tx in transactions]
        if len(leaf_nodes) % 2 != 0:
            leaf_nodes.append(leaf_nodes[-1])
        while len(leaf_nodes) > 1:
            new_level = []
            for i in range(0, len(leaf_nodes), 2):
                combined_hash = hashlib.sha3_512(str(leaf_nodes[i]).encode('utf-8') + str(leaf_nodes[i + 1]).encode('utf-8')).hexdigest()
                new_level.append(combined_hash)
            leaf_nodes = new_level
            if len(leaf_nodes) % 2 != 0 and len(leaf_nodes) != 1:
                leaf_nodes.append(leaf_nodes[-1])
        return leaf_nodes[0]
    
    def update_hash_rate(self):
        self.hash_rate_label.config(text=f"Hash Rate: {self.hash_rate} Gh/s")
        self.root.after(1000, self.update_hash_rate)

app = Flask(__name__)
@app.route('/update_wallet', methods=['POST'])
def update_wallet():
    data = request.get_json()
    message = data.get('message')
    address = data.get('address')
    decimals = data.get('decimals')
    reward = f"{float(data.get('amount')):.{decimals}f}"
    print(f"{address} rewarded {reward} {coin_name}")
    if message == 'approved':
        with open('wallet.json', 'r') as file:
            data = json.load(file)
        for entry in data:
            if entry['public_key'] == address:
                entry['amount'] = float(entry['amount']) + float(reward)
                entry['amount'] = f"{entry['amount']:.{decimals}f}"
                new_amount = entry['amount']
                break
        with open('wallet.json', 'w') as file:
            json.dump(data, file, indent=4)
        gui.sender_wallet_label.config(text=f"Welcome to {coin_name} Client\nCurrent Wallet: {gui.wallet.nickname}\nAmount: {new_amount} {coin_name}\n\t\t\t\t\t\t")
        return jsonify({"message": f"Mining pool rewarded {address} {reward} {coin_name}!"}), 200
    else:
        return jsonify({"message": "Wallet update for {address} failed. Reward queue?"}), 400

def run_flask_app():
    app.run(port=client_port)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    root = tk.Tk()
    gui = BlockchainGUI(root)
    root.mainloop()
