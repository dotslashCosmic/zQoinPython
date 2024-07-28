_Potential TODO List_
### Blockchain problems
1. **51% Attack Protection**: In the blockchain realm, an ever-present risk is the potential for a 51% attack, where a certain group gains more than 50% control. This can lead to manipulating transactions, executing double-spending schemes, or disrupting the validation of new transactions.
    - 1a. **Practical Byzantine Fault Tolerance**: PBFT is designed to achieve consensus even in the presence of faulty or malicious nodes. It involves a series of communication rounds between nodes and is known for its low-latency finality, making it suitable for private or consortium blockchains.

2. **High Energy Consumption**: Mining activities for cryptocurrencies consume a significant amount of energy.
    - 2a. **Proof of Burn**: Potentially go PoW to PoB, triggers at max coins infinitely.
    - 2b. **Proof of Stake**: Potentially go PoW to PoS once max coins are reached.

3. **SSRF Protection**: Allow wallets to confirm their IP/mac hash to be saved as a trusted source.

# client
1. **Encrypt Private Keys**: Implement AES encryption for storing private keys in `wallet.json`.
2. **Secure Signing Algorithm**: Replace the current signing method with ECDSA.
3. **Use HTTPS**: Update the network communication to use HTTPS instead of HTTP.
4. **Input Validation**: Implement input validation checks for transaction amounts and addresses.
5. **Hierarchical Deterministic Wallets (HD Wallets)**: Implement HD wallets to generate a tree of keys from a single seed.
6. **Multi-Signature Transactions**: Support multi-signature transactions for enhanced security.
7. **Transaction Fee Calculation**: Implement dynamic transaction fee calculation based on network conditions.
8. **Address Reuse Prevention**: Ensure that new addresses are generated for each transaction to enhance privacy.
9. **BIP-39 Mnemonic Phrases**: Implement BIP-39 for generating mnemonic phrases for wallet backup and recovery. *partial
10. **Partial Mine Rewards**: Potentially impliment partial PoW iteration confirmation

# host
1. **Encrypt Blockchain Data**: Implement encryption for storing the blockchain in `blockchain.json` using a secure encryption library like `cryptography`.
2. **Use HTTPS**: Update the network communication to use HTTPS instead of HTTP.
3. **Block Validation**: Implement comprehensive block validation rules to ensure the integrity of the blockchain. *partial
4. **Peer-to-Peer (P2P) Network**: Implement a P2P network for decentralized communication between nodes.
5. **Transaction Pool**: Maintain a pool of unconfirmed transactions to be included in future blocks.
6. **UTXO Model**: Implement the UTXO (Unspent Transaction Output) model for tracking transaction outputs.
7. **Blockchain Pruning**: Implement blockchain pruning to reduce storage requirements by removing old, spent transaction data.
