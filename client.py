import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import threading, time, requests, json, hashlib, os

class Wallet:
    def __init__(self, nickname, amount=0):
        self.private_key = self.generate_private_key()
        self.public_key = self.generate_public_key(self.private_key)
        self.nickname = nickname
        self.amount = amount

    def generate_private_key(self):
        return hashlib.sha3_512(os.urandom(64)).hexdigest()
        
    def generate_public_key(self, private_key):
        return 'zqn' + hashlib.sha3_512(private_key.encode('utf-8')).hexdigest()[-61:]

    def save_keys(self):
        if os.path.exists('wallet.json'):
            with open('wallet.json', 'r') as f:
                wallets = json.load(f)
        else:
            wallets = []
        wallets.append({
            'private_key': self.private_key,
            'public_key': self.public_key,
            'nickname': self.nickname,
            'amount': self.amount
        })
        with open('wallet.json', 'w') as f:
            json.dump(wallets, f, indent=4)

    def load_keys(self):
        with open('wallet.json', 'r') as f:
            keys = json.load(f)
            self.private_key = keys['private_key']
            self.public_key = keys['public_key']

def create_transaction(sender, receiver, amount):
    transaction = {
        'sender': sender,
        'receiver': receiver,
        'amount': amount
    }
    return transaction

def mine_block(transaction, wallet_address):
    url = 'http://localhost:5000/mine'

    payload = {
        'transaction': {
            'sender': transaction['sender'],
            'receiver': transaction['receiver'],
            'amount': transaction['amount']
        },
        'wallet': wallet_address
    }
    response = requests.post(url, json=payload)
    return response.json()

class BlockchainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blockchain GUI")
        self.mining = False
        self.hash_rate = 0
        if os.path.exists('wallet.json'):
            with open('wallet.json', 'r') as f:
                keys = json.load(f)[0]
            self.wallet = Wallet(keys['nickname'], keys['amount'])
            self.wallet.private_key = keys['private_key']
            self.wallet.public_key = keys['public_key']
        else:
            nickname = tk.simpledialog.askstring("Input", "Enter a nickname for the wallet:")
            if not nickname:
                messagebox.showerror("Input Error", "Nickname is required.")
                return
            self.wallet = Wallet(nickname)
            self.wallet.save_keys()
        self.sender_wallet_label = tk.Label(root, text=f"Current Wallet: {self.wallet.nickname}")
        self.sender_wallet_label.pack(pady=10)
        self.sender_wallet_entry = tk.Entry(root)
        self.sender_wallet_entry.pack(pady=10)
        self.sender_wallet_entry.insert(0, self.wallet.public_key)
        self.sender_wallet_entry.config(state='readonly')
        self.new_wallet_button = tk.Button(root, text="Create New Wallet", command=self.create_new_wallet)
        self.new_wallet_button.pack(pady=10)
        self.mining_wallet_label = tk.Label(root, text="Mining Wallet Address:")
        self.mining_wallet_label.pack(pady=10)
        self.mining_wallet_entry = tk.Entry(root)
        self.mining_wallet_entry.pack(pady=10)
        self.mining_wallet_entry.insert(0, self.wallet.public_key)
        self.mine_button = tk.Button(root, text="Mine", command=self.start_mining)
        self.mine_button.pack(pady=10)
        self.hash_rate_label = tk.Label(root, text="Hash Rate: 0 H/s")
        self.hash_rate_label.pack(pady=10)
        self.update_hash_rate()
        self.receiver_wallet_label = tk.Label(root, text="Receiver Wallet Address:")
        self.receiver_wallet_label.pack(pady=10)
        self.receiver_wallet_entry = tk.Entry(root)
        self.receiver_wallet_entry.pack(pady=10)
        self.amount_label = tk.Label(root, text="Amount:")
        self.amount_label.pack(pady=10)
        self.amount_entry = tk.Entry(root)
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
            self.start_button.config(text="Stop Mining")
            self.start_mining()
        else:
            self.start_button.config(text="Start Mining")

    def start_mining(self):
        self.mining = True
        self.mine_button.config(text="Stop Mining", command=self.stop_mining)
        threading.Thread(target=self.mine).start()

    def stop_mining(self):
        self.mining = False
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
        result = mine_block(transaction, self.wallet.public_key)
        messagebox.showinfo("Mining Result", result)

    def mine(self):
        while self.mining:

            # Fetch the latest block from the host
            response = requests.get('http://127.0.0.1:5000/blocks')
            if response.status_code == 200:
                blocks = response.json()
                previous_block = blocks[-1]
                previous_hash = previous_block['hash']
            else:
                print("Failed to fetch the latest block.")
                return

            # Fetch all previous transactions from the host
            response = requests.get('http://127.0.0.1:5000/transactions')
            if response.status_code == 200:
                transactions = response.json()
                transactions_data = json.dumps(transactions)
            else:
                print("Failed to fetch previous transactions.")
                return

            # Set the difficulty target
            difficulty = 4
            target = '0' * difficulty

            # Prepare the data to mine
            data = f"{previous_hash}{transactions_data}"
            start_time = time.time()
            result = hashlib.sha3_512(data.encode()).hexdigest()


            time.sleep(0.1)  # Increased delay to slow down mining process
            end_time = time.time()
            time_diff = end_time - start_time
            if time_diff == 0:
                self.hash_rate = float('inf')  # Handle zero time difference
            else:
                self.hash_rate = 1 / time_diff

            # Send the mined block to the host
            block_data = {
                'data': data,
                'hash': result,
                'hash_rate': self.hash_rate
            }

            response = requests.post('http://127.0.0.1:5000/add_block', json=block_data)
            if response.status_code == 200:
                print("Block successfully added to the blockchain.")
            else:
                print("Failed to add block to the blockchain.")
            print(f"Mined data: {result}")
            time.sleep(1)
        sender = self.sender_wallet_entry.get()
        receiver = self.receiver_wallet_entry.get()
        amount = self.amount_entry.get()
        if not sender or not receiver or not amount:
            messagebox.showerror("Input Error", "All fields are required.")
            return
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showerror("Input Error", "Amount must be a valid number.")
            return
        transaction = create_transaction(sender, receiver, str(amount))
        wallet_address = self.mining_wallet_entry.get()
        result = mine_block(transaction, wallet_address)
        messagebox.showinfo("Mining Result", result)

        def mine():
            start_time = time.time()
            print(start_time)
            while self.mining:
                data = "Some data to mine, algorithms and such"
                result = mine_block(data, self.wallet.public_key)
                time.sleep(0.1)
                end_time = time.time()
                print(end_time)
                self.hash_rate = 1 / (end_time - start_time)
                print(result)
                time.sleep(1)
        threading.Thread(target=mine).start()
        
    def update_hash_rate(self):
        self.hash_rate_label.config(text=f"Hash Rate: {self.hash_rate:.2f} H/s")
        self.root.after(1000, self.update_hash_rate)

if __name__ == '__main__':
    root = tk.Tk()
    gui = BlockchainGUI(root)
    root.mainloop()

