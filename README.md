
# zQoin Cryptocurrency Project

## Overview
This project is a simple implementation of a cryptocurrency named zQoin, based on SHA3-512 Proof of Work.
It includes a blockchain, wallets, and mining functionality. The project is divided into three main components:
- `host.py`: Starts the crypto node and hosts the blockchain and wallets.
- `client.py`: Mines zQoin crypto, and sends/receives transactions to/from wallets.
- `calculate.py`: Calculates the maximum supply of coins based on difficulty variables. (outdated)

## Features
- **Blockchain**: A basic implementation of a blockchain to manage transactions and mining.
- **Node Integration**: PBFT fault tolerence between P2P nodes that host the blockchain.
- **Wallets**: Create and manage wallets for storing zQoin.
- **Mining**: Mine zQoin using the `client.py` script.
- **Full Customizability**: Variables all ready to customize, in an easy to read format.

## Installation
To run this project, you need to have Python installed. Additionally, you need to install the following dependencies:

For the client and host:
```
$ pip install flask
$ pip install tkinter
```
Host only:
```
$ pip install flask-limiter
```

## Usage
### Starting the Crypto Node
To start the crypto node and host the blockchain and wallets, run:
```bash
$ python host.py
```

### Mining zQoin
To mine zQoin, run:
```bash
$ python client.py
```

### Calculating Maximum Supply
Outdated.
To calculate the maximum supply of zQoin, run:
```bash
$ python calculate.py
```

## Customization
You can customize various parameters in the `client.py` and `host.py` files:
- **client.py**:
  - `coin_name` Coin full name
  - `short_name` Coin short name
  - `client_port` 1-65535, integer 
  - `host_port` 1-65535, integer (cannot match client port)
  - `server_ip` Host server IP
- **host.py**:
  - `coin_name` Coin full name
  - `short_name` Coin short name
  - `client_port` 1-65535, integer
  - `host_port` 1-65535, integer (cannot match client port)
  - `base` Base difficulty
  - `max_base` Maximum difficulty
  - `a, b, c, d, e` Variables affecting speed of mining
  - `max_coin` Maximum amount of coins in circulation, ~462mb per 1m max_coin/reward, ~580 bytes per wallet
  - `reward` Base reward per block, float
  - `time_between_rewards` Minimum seconds between blocks
  - `consensus_count` How many validations is required to save block
  - `wallet_list_url` Wallet creation word list
  - `host_version_url` SHA3-512 of this file
  - `check` Validates the host against host version url hash
  - `node_consensus` Minimum nodes for consensus verification
  - `node_tolerance` Tolerance for faulty/malicious nodes
  - `local` Allows local IPs
  - `client_version` with the `client.py` `sha3-512` hash
  - `genesis_token` Genesis block token

## File Verification
This project includes [DotSlashVerify](https://github.com/dotslashCosmic/DotSlashVerify) hashes for the files to ensure their integrity.

## Contributing
Feel free to fork this project, submit issues and pull requests. Contributions are welcome!

## License
This project is licensed under the GPL-3.0 License.

### Milestones
- **7/27**: Got the mining pool working, woo!

---
