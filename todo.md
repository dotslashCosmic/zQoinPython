#Potential TODO List

## Blockchain problems
1. **High Energy Consumption**: Mining activities for cryptocurrencies consume a significant amount of energy. This has raised environmental concerns and calls for more sustainable alternatives.
  - 1a. **Proof of Burn**: Potentially go PoW to PoB, triggers at max coins infinitely.
  - 1b. **Proof of Stake**: Potentially go PoW to PoS once max coins are reached.
2. **Fair Distribution Mechanisms**: Implement fair distribution mechanisms such as airdrops or initial coin offerings that target a broader audience, including those with lower incomes or late adapters.
3. **Layer 1 and 2 Solutions**: Utilize Layer scaling solutions like sidechaining, or the Lightning Network for Bitcoin or Optimistic Rollups for Ethereum. These solutions process transactions off-chain and then settle them on-chain, reducing congestion.
  - 3a. **Sharding**: Implement sharding, which divides the blockchain into smaller, more manageable pieces (shards) that can process transactions in parallel.
4. **Zero-Knowledge Proofs**: Potentially implement zero-knowledge proofs (e.g., zk-SNARKs) to enhance privacy without compromising security.
 
## Todo list (priority order)
1. **Encrypt Private Keys**: Implement AES encryption for storing private keys in `wallet.json`.
2. **Encrypt Blockchain Data**: Implement encryption for storing the blockchain in `blockchain.json` using a secure encryption library like `cryptography`.
3. **Use HTTPS**: Update the network communication to use HTTPS instead of HTTP.
4. **Partial Mine Rewards**: Potentially impliment partial PoW iteration confirmation.
5. **Input Validation**: Implement input validation checks for transaction amounts and addresses.
6. **Hierarchical Deterministic Wallets (HD Wallets)**: Implement HD wallets to generate a tree of keys from a single seed.
7. **Transaction Pool**: Maintain a pool of unconfirmed transactions to be included in future blocks.
8. **Blockchain Pruning**: Implement blockchain pruning to reduce storage requirements by removing old, spent transaction data.
9. **Transaction Fee Calculation**: Implement dynamic transaction fee calculation based on network conditions.
10. **UTXO Model**: Implement the UTXO (Unspent Transaction Output) model for tracking transaction outputs.
11. **Address Reuse Prevention**: Ensure that new addresses are generated for each transaction to enhance privacy.
12. **Multi-Signature Transactions**: Support multi-signature transactions for enhanced security.
13. **Block Validation**: Implement comprehensive block validation rules to ensure the integrity of the blockchain. *partial
14. **Secure Signing Algorithm**: Replace the current signing method with ECDSA.
15. **BIP-39 Mnemonic Phrases**: Implement BIP-39 for generating mnemonic phrases for wallet backup and recovery. *partial
16. **Peer-to-Peer (P2P) Network**: Implement a P2P network for decentralized communication between nodes.
