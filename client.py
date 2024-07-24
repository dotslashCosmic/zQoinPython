#Author: dotslashCosmic
import sys
import tkinter as tk
from flask import Flask, request, jsonify
from tkinter import simpledialog
from tkinter import messagebox
from datetime import datetime
import threading, time, requests, json, hashlib, os, binascii, secrets

client_port = 5317
host_port = 5318
localip = f'http://127.0.0.1:{host_port}'
localhost = f'http://localhost:{host_port}'
coin_name = 'zQoin'
short_name = 'zqn'
if not len(short_name) == 3:
   print("Short name must be 3 characters. Defaulting.")
   short_name = 'zqn'

def generate_entropy(bits=128):
    return secrets.token_bytes(bits // 8)

def entropy_to_mnemonic(entropy):
    entropy_bits = bin(int.from_bytes(entropy, byteorder='big'))[2:].zfill(len(entropy) * 8)
    checksum_length = len(entropy_bits) // 32
    checksum = bin(int(hashlib.sha256(entropy).hexdigest(), 16))[2:].zfill(256)[:checksum_length]
    bits = entropy_bits + checksum
    response = requests.get('https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt')
    if response.status_code == 200:
        wordlist = response.text.splitlines()
    else:
        print("Failed to fetch wordlist.")
        return None
    words = [wordlist[int(bits[i:i+11], 2)] for i in range(0, len(bits), 11)]
    return ' '.join(words)

def mnemonic_to_seed(mnemonic, passphrase=''):
    mnemonic = mnemonic.encode('utf-8')
    salt = ('mnemonic' + passphrase).encode('utf-8')
    return hashlib.pbkdf2_hmac('sha512', mnemonic, salt, 2048, dklen=64)

class Wallet:
    def __init__(self, nickname, amount=0):
        self.entropy = generate_entropy()
        self.mnemonic = entropy_to_mnemonic(self.entropy)
        self.seed = mnemonic_to_seed(self.mnemonic)
        self.private_key = self.generate_private_key(self.seed)
        self.public_key = self.generate_public_key(self.private_key)
        self.nickname = nickname
        self.amount = amount

    def generate_private_key(self, seed):
        return hashlib.sha3_512(seed).hexdigest()

    def generate_public_key(self, private_key):
        return short_name + hashlib.sha3_512(private_key.encode('utf-8')).hexdigest()[-61:]

    def save_keys(self):
        url = localhost+'/wallet_exists'
        response = requests.post(url, json={'public_key': self.public_key})
        if not response.json().get('exists'):
            wallet_data = {
                'mnemonic': self.mnemonic,
                'seed': binascii.hexlify(self.seed).decode(),
                'private_key': self.private_key,
                'public_key': self.public_key,
                'nickname': self.nickname,
                'amount': '0',
            }
            url = localhost+'/create_wallet'
            response = requests.post(url, json=[wallet_data])
            if response.status_code == 200:
                with open('wallet.json', 'w') as f:
                    json.dump([wallet_data], f, indent=4)
            else:
                print("Wallet creation failed.")
                return

    def load_keys(self):
        url = localhost+'/get_wallet'
        response = requests.post(url, json={'public_key': self.public_key})
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
                print("wallet.json does not exist.")
        else:
            print("Failed to load keys from the server.")

def create_transaction(sender, receiver, amount, private_key):
    transaction = {
        'sender': sender,
        'receiver': receiver,
        'amount': amount
    }
    transaction['signature'] = sign_transaction(transaction, private_key)
    return transaction

def sign_transaction(transaction, private_key):
    transaction_string = json.dumps(transaction, sort_keys=True)
    return hashlib.sha3_512((transaction_string + private_key).encode('utf-8')).hexdigest()

def submit_transaction(transaction):
    url = localhost + '/transactions'
    response = requests.post(url, json=transaction)
    return response.json()

def get_blockchain_state():
    url = localhost + '/blocks'
    response = requests.get(url)
    return response.json()

def send_transaction(transaction, wallet_address):
    url = localhost + '/send_transaction'
    payload = {
        'transaction': {
            'sender': transaction['sender'],
            'receiver': transaction['receiver'],
            'amount': transaction['amount']
        },
        'wallet': wallet_address
    }
    response = requests.post(url, json=payload)

def get_index():
    response = requests.get(localip + '/index')
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
            response = requests.post(localip+'/get_wallet', json={'public_key': self.wallet.public_key})
            response_keys = response.json()
            if not (self.wallet.private_key == response_keys['private_key'] and 
                    self.wallet.public_key == response_keys['public_key'] and 
                    self.wallet.amount == response_keys['amount']):
                return print("Fake wallet.")
        else:
            nickname = tk.simpledialog.askstring("Input", "Enter a nickname for the wallet:")
            if not nickname:
                messagebox.showerror("Input Error", "Nickname is required.")
                return
            self.wallet = Wallet(nickname)
            self.wallet.save_keys()
        self.check_hash_with_server()
        self.sender_wallet_label = tk.Label(root, text=f"Welcome to {coin_name} Client\nCurrent Wallet: {self.wallet.nickname}\nAmount: {self.wallet.amount} {coin_name}\n\t\t\t\t\t\t")
        self.sender_wallet_label.pack(pady=10)
        self.sender_wallet_entry = tk.Entry(root)
        self.sender_wallet_entry.pack(pady=10)
        self.sender_wallet_entry.insert(0, self.wallet.public_key)
        self.sender_wallet_entry.config(state='readonly')
        self.new_wallet_button = tk.Button(root, text="Create New Wallet", command=self.create_new_wallet)
        self.new_wallet_button.pack(pady=10)
        self.create_transaction_button = tk.Button(root, text="Create Transaction", command=self.create_transaction)
        self.create_transaction_button.pack(pady=10)
        self.submit_transaction_button = tk.Button(root, text="Submit Transaction", command=self.submit_transaction)
        self.submit_transaction_button.pack(pady=10)
        self.mine_button = tk.Button(root, text="Mine", command=self.start_mining)
        self.mine_button.pack(pady=10)
        self.hash_rate_label = tk.Label(root, text="Hash Rate: 0 H/s")
        self.hash_rate_label.pack(pady=10)
        self.update_hash_rate()

    def check_hash_with_server(self):
        url = localip+'/check_client'
        data = {
            'client_hash': self.client_hash,
            'coin_name': coin_name,
            'client_wallet': self.wallet.public_key
        }
        response = requests.post(url, json=data)
        if response.status_code == 200 and response.json().get('status') == 'success':
            return
        else:
            print("Failure to verify client.")
            sys.exit(1)

    def create_transaction(self):
        receiver = self.receiver_wallet_entry.get()
        amount = self.amount_entry.get()
        transaction = create_transaction(self.wallet.public_key, receiver, amount, self.wallet.private_key)
        self.transaction = transaction
        self.transaction_status_label.config(text="Transaction Created")

    def submit_transaction(self):
        if hasattr(self, 'transaction'):
            response = submit_transaction(self.transaction)
            self.transaction_status_label.config(text="Transaction Submitted")
        else:
            self.transaction_status_label.config(text="No Transaction to Submit")
        self.receiver_wallet_label = tk.Label(root, text="Receiver Wallet Address:")
        self.receiver_wallet_label.pack(pady=10)
        self.receiver_wallet_entry = tk.Entry(root)
        self.receiver_wallet_entry.pack(pady=10)
        self.amount_label = tk.Label(root, text="Amount:")
        self.amount_label.pack(pady=10)
        self.amount_entry = tk.Entry(root)
        self.amount_entry.pack(pady=10)
        self.transaction_status_label = tk.Label(root, text="")
        self.transaction_status_label.pack(pady=10)
        self.amount_entry.pack(pady=10)
        self.send_button = tk.Button(root, text="Send", command=self.send_transaction)
        self.send_button.pack(pady=10)

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

    def send_transaction(self):
        receiver = self.receiver_wallet_entry.get()
        amount = self.amount_entry.get()
        if not receiver or not amount:
            messagebox.showerror("Input Error", "All fields are required.")
            return
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showerror("Input Error", "Amount must be a valid number.")
            return
        transaction = create_transaction(self.wallet.public_key, receiver, str(amount))
        result = send_transaction(transaction, self.wallet.public_key)
        messagebox.showinfo("Mining Result", result)
        
    def mine(self):
        index = 0
        while self.mining:
            response = requests.get(localip + '/difficulty')
            if response.status_code == 200:
                difficulty_response = response.json()
                difficulty = difficulty_response['difficulty']
                target = difficulty_response['target']
                max_base = difficulty_response['max_base']
            else:
                print("Failed to fetch difficulty.")
                return
            if index >= max_base:
                print(f"Reached the maximum limit of {coin_name} in circulation. Stopping mining.")
                break
            response = requests.get(localip+"/blocks")
            if response.status_code == 200:
                blocks = response.json()
                previous_block = blocks[-1]
                previous_index = previous_block['index']
                previous_hash = previous_block['hash']
            else:
                print("Failed to fetch the latest block.")
                return
            response = requests.get(localip+'/transactions')
            if response.status_code == 200:
                transactions = response.json()
                transactions_data = json.dumps(transactions)
            else:
                print("Failed to fetch previous transactions.")
                return
            data = f"{previous_hash}{transactions_data}"
            start_time = time.time()
            result = hashlib.sha3_512(data.encode()).hexdigest()
            time.sleep(0.001)
            end_time = time.time()
            time_diff = end_time - start_time
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
                'hash': result,
                'hash_rate': self.hash_rate,
                'miner': self.wallet.public_key
            }
            response = requests.post(localip+'/add_block', json=block_data)
            if response.status_code == 200:
                block_time = datetime.fromtimestamp(int(end_time)).strftime('%m/%d/%Y %H:%M:%S')
                print(f"Block {previous_index+1} mined at difficulty {difficulty}!\nMined data: {result}")
                index += 1
            else:
                print("Failed to add block to the blockchain.")
                self.stop_mining()

        def mine():
            start_time = time.time()
            while self.mining:
                data = f"GENESIS{coin_name}GENESIS"
                result = send_transaction(data, self.wallet.public_key)
                end_time = time.time()
                time_diff = end_time - start_time
                if time_diff == 0:
                    self.hash_rate = float('inf')
                else:
                    self.hash_rate = 1 / (end_time - start_time)
                print(result)
        threading.Thread(target=mine).start()
        
    def update_hash_rate(self):
        self.hash_rate_label.config(text=f"Hash Rate: {self.hash_rate} H/s")
        self.root.after(1000, self.update_hash_rate)

app = Flask(__name__)
    
@app.route('/update_wallet', methods=['POST'])
def update_wallet():
    data = request.get_json()
    message = data.get('message')
    address = data.get('address')
    reward = int(data.get('amount'))
    if message == 'approved':
        with open('wallet.json', 'r') as file:
            data = json.load(file)
        for entry in data:
            if entry['public_key'] == address:
                entry['amount'] = int(entry['amount'])
                entry['amount'] += reward
                new_amount = entry['amount']
                break
        with open('wallet.json', 'w') as file:
            json.dump(data, file, indent=4)
        gui.sender_wallet_label.config(text=f"Welcome to {coin_name} Client\nCurrent Wallet: {gui.wallet.nickname}\nAmount: {new_amount} {coin_name}\n\t\t\t\t\t\t")
        return jsonify({"message": f"Mining pool rewarded {address}!"}), 200
    else:
        print("Wallet update failed.")

def run_flask_app():
    app.run(port=client_port)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    root = tk.Tk()
    gui = BlockchainGUI(root)
    root.mainloop()
