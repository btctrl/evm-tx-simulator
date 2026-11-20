# evm-tx-simulator

Asynchronous pre-flight EVM transaction simulator and EIP-1559 gas estimator built with Python and `web3.py`. Validates smart contract calls via `eth_call` before broadcasting to catch execution reverts and optimize gas limits.

## Features
- **Revert Prevention:** Simulates state transitions via `eth_call` and decodes smart contract revert reasons prior to signing or broadcasting.
- **EIP-1559 Fee Engineering:** Queries live block `baseFeePerGas` and `maxPriorityFeePerGas` concurrently to compute accurate gas budgets and safety buffers.
- **Zero-Key Dry Runs:** Built-in demonstration verifying both valid contract interactions and prevented balance-exceeding reverts on Base Mainnet.

## Quickstart

```bash
git clone https://github.com/btctrl/evm-tx-simulator
cd evm-tx-simulator
pip install -r requirements.txt
python simulator.py
```

## Example Output

```text
18:05:09 | INFO | Connected to Base Mainnet | Running Pre-Flight Simulations...
18:05:10 | INFO | [SCENARIO 1: Valid Approve] Success: True | Gas: 38704 (Buffered: 44509) | MaxFee: 0.015295 Gwei | Est. Cost: 0.00000059 ETH
18:05:11 | WARNING | [SCENARIO 2: Invalid Transfer] Success: False | Prevented On-Chain Revert! Reason: execution reverted: ERC20: transfer amount exceeds balance
```
