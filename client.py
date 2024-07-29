#Author: dotslashCosmic
import threading, time, requests, json, hashlib, os, binascii, secrets, sys, uuid
import tkinter as tk
from flask import Flask, request, jsonify
from tkinter import simpledialog
from tkinter import messagebox
from datetime import datetime

client_port = 5317 #int, 1-65535
host_port = 5318 #int, 1-65535
server_ip = f'http://127.0.0.1:{host_port}' #Server IP, future update
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

def generate_entropy(bits=128):
    return secrets.token_bytes(bits // 8)

def mnemonic_to_seed(mnemonic, passphrase=''):
    mnemonic = mnemonic.encode('utf-8')
    salt = ('mnemonic' + passphrase).encode('utf-8')
    return hashlib.pbkdf2_hmac('sha3_512', mnemonic, salt, 2048, dklen=64)

class Wallet:
    def __init__(self, nickname, amount=0):
        self.entropy = generate_entropy()
        self.mnemonic = self.fetch_mnemonic()
        self.seed = mnemonic_to_seed(self.mnemonic)
        self.private_key = self.generate_private_key(self.seed)
        self.public_key = self.generate_public_key(self.private_key)
        self.nickname = nickname
        self.amount = amount
        
    def trust_hash(self):
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
        trust_hash = hashlib.sha3_512((mac_address + self.public_key).encode()).hexdigest()
        return trust_hash
        
    def fetch_mnemonic(self):
        response = requests.get(server_ip + '/wallet_list')
        if response.status_code == 200:
            return response.json().get('mnemonic')
        else:
            print("Failed to fetch mnemonic.")
            return None

    def generate_private_key(self, seed):
        return hashlib.sha3_512(seed).hexdigest()

    def generate_public_key(self, private_key):
        hash_length = 64 - len(short_name)
        return short_name + hashlib.sha3_512(private_key.encode('utf-8')).hexdigest()[-hash_length:]

    def save_keys(self):
        url = server_ip+'/wallet_exists'
        response = requests.post(url, json={'public_key': self.public_key})
        f_amount = '{:.{}f}'.format(0, decimals)
        if not response.json().get('exists'):
            wallet_data = {
                'mnemonic': self.mnemonic,
                'seed': binascii.hexlify(self.seed).decode(),
                'private_key': self.private_key,
                'public_key': self.public_key,
                'nickname': self.nickname,
                'coin_name': coin_name,
                'amount': f_amount
            }
            trust = tk.Tk()
            trust.withdraw()  # Hide the main window
            result = messagebox.askyesno("Trust This Device", f"Do you want to save this computer as a trusted source for {self.public_key}?")
            if result:
                wallet_data['trust_hash'] = self.trust_hash()
            else:
                wallet_data['trust_hash'] = False
            print("Generating wallet...")
            url = server_ip+'/create_wallet'
            response = requests.post(url, json=[wallet_data])
            if response.status_code == 200:
                wallet_data.pop('coin_name', None)
                with open('wallet.json', 'w') as f:
                    json.dump([wallet_data], f, indent=4)
            else:
                print("Wallet creation failed.")
                return

    def load_keys(self):
        is_trusted = self.trust_hash()
        url = server_ip+'/get_wallet'
        response = requests.post(url, json={'public_key': self.public_key, 'trust_hash': is_trusted})
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

def get_blockchain_state():
    url = server_ip+'/blocks'
    response = requests.get(url)
    return response.json()

def get_index():
    response = requests.get(server_ip+'/index')
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
        print(self.client_hash)
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
            response = requests.post(server_ip+'/get_wallet', json={'public_key': self.wallet.public_key})
            response_keys = response.json()
            print(response_keys)
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
        url = server_ip + '/check_client'
        data = {
            'client_hash': self.client_hash
        }
        response = requests.post(url, json=data)
        if response.status_code == 200:
            response_json = response.json()
            if 'decimals' in response_json:
                decimals = response_json['decimals']
                return decimals
            else:
                print("Decimal key not found in the response.")
                sys.exit(1)
        else:
            print("Failure to verify client.")
            sys.exit(1)

    def create_new_wallet(self):
        nickname = tk.simpledialog.askstring("Input", "Enter a nickname for the wallet:")
        if not nickname:
            messagebox.showerror("Input Error", "Nickname is required.")
            return
        self.wallet = Wallet(nickname)
        self.wallet.save_keys()
        self.wallet_label.config(text=f"Wallet Address: {self.wallet.public_key} | Amount: {self.wallet.amount}")
        self.mining_wallet_entry.delete(0, tk.END)
        self.mining_wallet_entry.insert(0, self.wallet.public_key)
        self.mining = not self.mining
        if self.mining:
            self.start_button.config(text="---Stop Mining---")
            self.start_mining()
        else:
            self.start_button.config(text="Mine")

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
            response = requests.get(server_ip+'/difficulty')
            if response.status_code == 200:
                difficulty_response = response.json()
                difficulty = difficulty_response['difficulty']
                target = difficulty_response['target']
                transactions = difficulty_response['transactions']
                nonce = difficulty_response['nonce']
                limit = difficulty_response['limit']
                if limit == True:
                    print(f"End of block rewards.")
            else:
                print("Failed to fetch difficulty.")
                self.stop_mining()
                return
            response = requests.get(server_ip+"/blocks")
            if response.status_code == 200:
                blocks = response.json()
                previous_block = blocks[-1]
                previous_index = previous_block['index']
                previous_hash = previous_block['hash']
            else:
                print("Failed to fetch the latest block.")
                self.stop_mining()
                return
            new_index = previous_index + 1
            start_time = int(time.time())
            form_time = datetime.fromtimestamp(int(start_time)).strftime('%m/%d/%Y %H:%M:%S')
            print(f"PoW for block {new_index} at difficulty {difficulty} starting at {form_time}...")
            nonce, new_hash, new_transactions = self.proof_of_work(new_index, previous_hash, start_time, transactions, nonce, difficulty)
            data = f"{new_hash}{new_transactions}{nonce+1}"
            end_time = time.time()
            time_diff = end_time - start_time
            print(f"Time to mine block {new_index}: {time_diff:.2f}s")
            if time_diff == 0:
                self.hash_rate = float('inf')
            else:
                self.hash_rate = 1 / time_diff
            block_data = {
                'data': data,
            }
            first_hash = block_data['data'].split('[')[0].strip()
            data_part = block_data['data'].split('[')[1].strip(']')
            hashes = [hash.strip().strip('"') for hash in data_part.split(',')]
            last_10_hashes = first_hash+str(hashes[-10:])
            block_data = {
                'data': last_10_hashes,
                'new_nonce': nonce,
                'new_hash': new_hash,
                'new_transactions': new_transactions,
                'hash_rate': self.hash_rate,
                'miner': self.wallet.public_key
            }
            print("Waiting for consensus...")
            response = requests.post(server_ip+'/add_block', json=block_data)
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

    def proof_of_work(self, index, previous_hash, start_time, transactions, nonce, difficulty):
        for _ in range(difficulty):
            proof_hash = hashlib.sha3_512(f"{index}{previous_hash}{start_time}{transactions}{nonce}{difficulty}".encode('utf-8')).hexdigest()
            nonce += 1
            hash = hashlib.sha3_512(f"{index}{proof_hash}{start_time}{transactions}{nonce}{difficulty}".encode('utf-8')).hexdigest()     
        return nonce, hash, transactions
            
    def update_hash_rate(self):
        self.hash_rate_label.config(text=f"Hash Rate: {self.hash_rate} H/s")
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
