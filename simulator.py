import asyncio
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.exceptions import ContractLogicError
from typing import Any, Dict, Optional, Tuple


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evm-tx-simulator")

RPC_URL = os.getenv("RPC_URL", "https://base-rpc.publicnode.com")

USDC_BASE = AsyncWeb3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
SAMPLE_SENDER = AsyncWeb3.to_checksum_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
SAMPLE_SPENDER = AsyncWeb3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")

MINIMAL_ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


@dataclass
class SimulationResult:
    success: bool
    gas_estimate: int
    gas_limit_buffered: int
    max_fee_gwei: Decimal
    priority_fee_gwei: Decimal
    estimated_cost_eth: Decimal
    revert_reason: Optional[str] = None


class EvmTxSimulator:
    def __init__(self, rpc_url: str, gas_buffer_multiplier: float = 1.15) -> None:
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.gas_buffer = Decimal(str(gas_buffer_multiplier))

    async def get_eip1559_fees(self) -> Tuple[int, int]:
        latest_block, priority_fee = await asyncio.gather(
            self.w3.eth.get_block("latest"),
            self.w3.eth.max_priority_fee,
        )
        base_fee = latest_block.get("baseFeePerGas", 0)
        max_fee_per_gas = int(base_fee * 2) + priority_fee
        return max_fee_per_gas, priority_fee

    async def simulate_tx(self, tx_params: Dict[str, Any]) -> SimulationResult:
        max_fee, priority_fee = await self.get_eip1559_fees()
        max_fee_gwei = Decimal(max_fee) / Decimal(10**9)
        priority_fee_gwei = Decimal(priority_fee) / Decimal(10**9)

        try:
            # 1. Dry-run execution via eth_call to catch reverts
            await self.w3.eth.call(tx_params)

            # 2. Estimate exact gas consumption
            raw_gas = await self.w3.eth.estimate_gas(tx_params)
            buffered_gas = int(Decimal(raw_gas) * self.gas_buffer)
            est_cost_eth = Decimal(raw_gas * max_fee) / Decimal(10**18)

            return SimulationResult(
                success=True,
                gas_estimate=raw_gas,
                gas_limit_buffered=buffered_gas,
                max_fee_gwei=max_fee_gwei,
                priority_fee_gwei=priority_fee_gwei,
                estimated_cost_eth=est_cost_eth,
            )

        except ContractLogicError as exc:
            return SimulationResult(
                success=False,
                gas_estimate=0,
                gas_limit_buffered=0,
                max_fee_gwei=max_fee_gwei,
                priority_fee_gwei=priority_fee_gwei,
                estimated_cost_eth=Decimal(0),
                revert_reason=str(exc),
            )
        except Exception as exc:
            return SimulationResult(
                success=False,
                gas_estimate=0,
                gas_limit_buffered=0,
                max_fee_gwei=max_fee_gwei,
                priority_fee_gwei=priority_fee_gwei,
                estimated_cost_eth=Decimal(0),
                revert_reason=getattr(exc, "message", str(exc)),
            )


async def run_demo() -> None:
    simulator = EvmTxSimulator(rpc_url=RPC_URL, gas_buffer_multiplier=1.15)
    if not await simulator.w3.is_connected():
        raise ConnectionError(f"Failed to connect to RPC: {RPC_URL}")

    usdc = simulator.w3.eth.contract(address=USDC_BASE, abi=MINIMAL_ERC20_ABI)
    logger.info("Connected to Base Mainnet | Running Pre-Flight Simulations...\n")

       # Scenario 1: Valid ERC-20 approve call
    valid_tx = await usdc.functions.approve(SAMPLE_SPENDER, 1_000_000).build_transaction(
        {"from": SAMPLE_SENDER, "value": 0, "gas": 100_000}
    )
    res_valid = await simulator.simulate_tx(valid_tx)
    logger.info(
        f"[SCENARIO 1: Valid Approve] Success: {res_valid.success} | "
        f"Gas: {res_valid.gas_estimate} (Buffered: {res_valid.gas_limit_buffered}) | "
        f"MaxFee: {res_valid.max_fee_gwei:.6f} Gwei | Est. Cost: {res_valid.estimated_cost_eth:.8f} ETH"
    )

    # Scenario 2: Failing ERC-20 transfer (exceeds balance -> expected revert)
    failing_tx = await usdc.functions.transfer(SAMPLE_SPENDER, 10**18).build_transaction(
        {"from": SAMPLE_SENDER, "value": 0, "gas": 100_000}
    )



if __name__ == "__main__":
    asyncio.run(run_demo())
