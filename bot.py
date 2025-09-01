#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rome Martius (EVM-compatible) multi-contract deploy & interact bot.

- Reads accounts from account.txt (supports multiple formats).
- Optional proxies from proxy.txt in many common formats.
- Compiles a single Solidity file containing many contracts (contracts.sol).
- Menu with random/manual deploy selection and per-contract interactions.
- Pretty, colored output and summary table per wallet using Rich.
- Waits for on-chain receipts between steps.
- Designed to be resilient if contracts change: interaction steps are checked
  at runtime and skipped if a method is missing (no hard failure).

Run: python3 bot.py
"""

import os
import re
import json
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import box

from web3 import Web3
from web3.middleware.proof_of_authority import extra_data_middleware as geth_poa_middleware
from web3.types import TxReceipt

from requests import Session
from eth_account import Account

# solcx for dynamic compilation
from solcx import compile_standard, install_solc, set_solc_version

console = Console()

DEFAULT_RPC = "https://martius-i.testnet.romeprotocol.xyz"
CHAIN_ID = 121214  # Rome Testnet Martius
CURRENCY = "rSOL"
SOLC_VERSION = "0.8.24"

CONTRACTS_FILE = "contracts.sol"
ACCOUNTS_FILE = "account.txt"
PROXIES_FILE = "proxy.txt"
ARTIFACTS_DIR = "artifacts"

# ---------- Utilities ----------

def read_file_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

def parse_account_line(line: str) -> Tuple[str, str]:
    """
    Accept formats:
      - 0xPRIVATEKEY
      - ADDRESS,PRIVATEKEY
      - PRIVATEKEY,ADDRESS
      - ADDRESS|PRIVATEKEY
      - PRIVATEKEY|ADDRESS
    Returns (address, private_key_hex)
    """
    line = line.strip()
    # If it's a raw private key
    if re.fullmatch(r"0x[0-9a-fA-F]{64}", line):
        pk = line
        addr = Account.from_key(pk).address
        return addr, pk

    # Try split by common delimiters
    for delim in [",", "|", ";", " "]:
        if delim in line:
            parts = [p.strip() for p in line.split(delim) if p.strip()]
            if len(parts) == 2:
                a, b = parts
                # Decide which is which
                if re.fullmatch(r"0x[0-9a-fA-F]{40}", a) and re.fullmatch(r"0x[0-9a-fA-F]{64}", b):
                    return a, b
                if re.fullmatch(r"0x[0-9a-fA-F]{64}", a) and re.fullmatch(r"0x[0-9a-fA-F]{40}", b):
                    addr = Account.from_key(a).address
                    if addr.lower() != b.lower():
                        console.print(f"[yellow]Warning:[/yellow] Provided address doesn't match key; using derived address.")
                    return addr, a
    raise ValueError(f"Unrecognized account format: {line}")

def parse_proxy_line(line: str) -> Dict[str, str]:
    """
    Accept formats:
      - ip:port
      - http://ip:port
      - https://ip:port
      - socks5://ip:port
      - socks5h://user:pass@ip:port
      - user:pass@ip:port (assume http)
      Returns a 'proxies' dict usable by requests.Session.
    """
    line = line.strip()

    # If bare user:pass@ip:port -> assume http
    if re.fullmatch(r"[^:@]+:[^:@]+@[^:@]+:\d+", line):
        return {"http": f"http://{line}", "https": f"http://{line}"}

    # If bare ip:port -> assume http
    if re.fullmatch(r"[^:@]+:\d+", line):
        return {"http": f"http://{line}", "https": f"http://{line}"}

    # If full scheme given
    if re.match(r"^(http|https|socks4|socks5|socks5h)://", line):
        return {"http": line, "https": line}

    # Fallback: treat as http
    return {"http": f"http://{line}", "https": f"http://{line}"}

def load_accounts() -> List[Tuple[str, str]]:
    lines = read_file_lines(ACCOUNTS_FILE)
    accs: List[Tuple[str, str]] = []
    for ln in lines:
        try:
            accs.append(parse_account_line(ln))
        except Exception as e:
            console.print(f"[red]Skip account line:[/red] {ln} -> {e}")
    return accs

def load_proxies() -> List[Dict[str, str]]:
    lines = read_file_lines(PROXIES_FILE)
    proxies: List[Dict[str, str]] = []
    for ln in lines:
        try:
            proxies.append(parse_proxy_line(ln))
        except Exception as e:
            console.print(f"[red]Skip proxy line:[/red] {ln} -> {e}")
    return proxies

# ---------- Web3 Setup ----------

def make_web3(rpc_url: str, proxies: Optional[Dict[str, str]] = None) -> Web3:
    session = Session()
    if proxies:
        session.proxies.update(proxies)
    provider = Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 60, "session": session})
    w3 = Web3(provider)
    # Rome uses EVM compatibility; in case of PoA-style, attach middleware
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

# ---------- Compilation ----------

def ensure_compiler() -> None:
    try:
        set_solc_version(SOLC_VERSION)
    except Exception:
        install_solc(SOLC_VERSION)
        set_solc_version(SOLC_VERSION)

def compile_contracts(sol_path: str) -> Dict:
    ensure_compiler()
    source = open(sol_path, "r", encoding="utf-8").read()

    console.print("[cyan]Compiling contracts...[/cyan]")
    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                os.path.basename(sol_path): {"content": source}
            },
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode.object", "metadata"]}
                },
            },
        }
    )
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(os.path.join(ARTIFACTS_DIR, "combined.json"), "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2)
    return compiled

# ---------- Interaction helpers ----------

INTERACTION_CANDIDATES = [
    ("Greeter", "setGreeting", ["Hello " + str(random.randint(1, 9999))]),
    ("Counter", "increment", []),
    ("SimpleStorage", "set", [random.randint(1, 10**6)]),
    ("Faucet", "drip", []),
    ("YesNoVote", "vote", [bool(random.getrandbits(1))]),
    ("SimpleToken", "mint", [10**15]),
    ("SimpleNFT", "mint", []),
    ("Registry", "setRecord", ["key", "value"]),
    ("TimeNote", "setNote", ["note " + str(random.randint(1, 9999))]),
    ("Pinger", "ping", []),
]

def get_contract_abi_and_bytecode(compiled: Dict, contract_name: str) -> Tuple[List, str]:
    file_key = list(compiled["contracts"].keys())[0]
    data = compiled["contracts"][file_key][contract_name]
    abi = data["abi"]
    bytecode = data["evm"]["bytecode"]["object"]
    return abi, bytecode

def safe_build_contract(w3: Web3, abi: List, bytecode: Optional[str] = None, address: Optional[str] = None):
    if address:
        return w3.eth.contract(address=address, abi=abi)
    else:
        return w3.eth.contract(abi=abi, bytecode=bytecode)

# ---------- Core logic ----------

@dataclass
class WalletStats:
    deployed: int = 0
    interacted: int = 0
    failed: int = 0

@dataclass
class RunContext:
    w3: Web3
    compiled: Dict
    proxies_used: Optional[Dict[str, str]] = None
    stats: Dict[str, WalletStats] = field(default_factory=dict)

def send_and_wait(w3: Web3, tx) -> TxReceipt:
    tx_hash = w3.eth.send_raw_transaction(tx)
    console.print(f"[dim]Tx sent:[/dim] [bold]{tx_hash.hex()}[/bold]")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    status = receipt.status
    if status == 1:
        console.print(f"[green]SUCCESS[/green] in block {receipt.blockNumber}")
    else:
        console.print(f"[red]FAILED[/red] in block {receipt.blockNumber}")
    return receipt

def sign_build_send(w3: Web3, acct, tx_dict: Dict) -> TxReceipt:
    tx_dict["nonce"] = w3.eth.get_transaction_count(acct.address)
    if "chainId" not in tx_dict:
        tx_dict["chainId"] = w3.eth.chain_id
    # Let node estimate if gas not supplied
    if "gas" not in tx_dict:
        tx_dict["gas"] = w3.eth.estimate_gas(tx_dict)
    if "maxFeePerGas" not in tx_dict or "maxPriorityFeePerGas" not in tx_dict:
        # fallback to legacy if EIP-1559 not supported
        try:
            base = w3.eth.gas_price
            tx_dict["gasPrice"] = base
            tx_dict.pop("maxFeePerGas", None)
            tx_dict.pop("maxPriorityFeePerGas", None)
        except Exception:
            pass
    signed = acct.sign_transaction(tx_dict)
    return send_and_wait(w3, signed.rawTransaction)

def deploy_contract(ctx: RunContext, acct, name: str) -> Optional[str]:
    try:
        abi, bytecode = get_contract_abi_and_bytecode(ctx.compiled, name)
        Contract = safe_build_contract(ctx.w3, abi, bytecode=bytecode)
        # Handle constructors smartly
        constructor_args = {
            "Greeter": ["Hello Rome"],
        }.get(name, [])
        tx = Contract.constructor(*constructor_args).build_transaction({
            "from": acct.address,
            "value": 0
        })
        console.print(f"[cyan]Deploying {name} from {acct.address}...[/cyan]")
        rcpt = sign_build_send(ctx.w3, acct, tx)
        if rcpt.status == 1:
            addr = rcpt.contractAddress
            console.print(f":check_mark_button:  [bold green]{name}[/bold green] deployed at [bold]{addr}[/bold]")
            return addr
        else:
            console.print(f":cross_mark: [red]{name} deploy failed[/red]")
            return None
    except Exception as e:
        console.print(f"[red]Deploy error {name}:[/red] {e}")
        return None

def interact_with(ctx: RunContext, acct, name: str, at: str, max_retries: int = 1) -> bool:
    try:
        abi, _ = get_contract_abi_and_bytecode(ctx.compiled, name)
        contract = safe_build_contract(ctx.w3, abi, address=at)

        # Find candidate call for this name
        cand = next((c for c in INTERACTION_CANDIDATES if c[0] == name), None)
        if not cand:
            console.print(f"[yellow]No interaction template for {name}, skipping.[/yellow]")
            return False
        _, fn_name, args = cand
        if not any(item.get("name") == fn_name for item in abi if item.get("type") == "function"):
            console.print(f"[yellow]{name} has no '{fn_name}' method, skipping.[/yellow]")
            return False

        fn = getattr(contract.functions, fn_name)(*args)
        tx = fn.build_transaction({"from": acct.address, "value": 0})
        console.print(f"[magenta]Interacting {name}.{fn_name}() from {acct.address}[/magenta]")
        rcpt = sign_build_send(ctx.w3, acct, tx)
        return rcpt.status == 1
    except Exception as e:
        if max_retries > 0:
            console.print(f"[yellow]Retrying interaction for {name} due to: {e}[/yellow]")
            return interact_with(ctx, acct, name, at, max_retries - 1)
        console.print(f"[red]Interaction error {name}:[/red] {e}")
        return False

# ---------- Menu & Flow ----------

def select_mode() -> str:
    choice = Prompt.ask(
        "Select mode",
        choices=["random", "manual"],
        default="random"
    )
    return choice

def ask_counts() -> Tuple[int, int]:
    d = IntPrompt.ask("How many deployments?", default=5, show_default=True)
    i = IntPrompt.ask("How many interactions per deployed contract?", default=2, show_default=True)
    return d, i

def ask_delays() -> Tuple[float, float]:
    mn = float(Prompt.ask("Min delay between tx (sec)", default="0.5"))
    mx = float(Prompt.ask("Max delay between tx (sec)", default="2.0"))
    if mx < mn:
        mn, mx = mx, mn
    return mn, mx

def maybe_use_proxy(proxies_list: List[Dict[str,str]]) -> Optional[Dict[str,str]]:
    if not proxies_list:
        return None
    use = Confirm.ask("Use proxy from proxy.txt?", default=False)
    if not use:
        return None
    # Round-robin or random select; here choose random for simplicity
    return random.choice(proxies_list)

def pick_contracts_manual(compiled: Dict) -> List[str]:
    file_key = list(compiled["contracts"].keys())[0]
    names = list(compiled["contracts"][file_key].keys())
    console.print(Panel("\n".join(f"{idx+1}. {n}" for idx, n in enumerate(names)), title="Available Contracts"))
    raw = Prompt.ask("Enter numbers separated by comma (e.g., 1,3,5)", default="1,2")
    idxs = []
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit():
            idxs.append(int(x)-1)
    selected = [names[i] for i in idxs if 0 <= i < len(names)]
    if not selected:
        selected = names
    return selected

def pick_contracts_random(compiled: Dict, count: int) -> List[str]:
    file_key = list(compiled["contracts"].keys())[0]
    names = list(compiled["contracts"][file_key].keys())
    if count >= len(names):
        random.shuffle(names)
        return names
    return random.sample(names, count)

def main():
    console.print(Panel.fit("[bold]Rome Martius Multi-Contract Deployer[/bold]\nEVM Chain ID: 121214 | Currency: rSOL", box=box.ROUNDED))

    rpc = Prompt.ask("RPC URL", default=DEFAULT_RPC)
    console.print(f"RPC: [bold]{rpc}[/bold]")

    accounts = load_accounts()
    if not accounts:
        console.print("[red]No accounts found in account.txt[/red]")
        return

    proxies_list = load_proxies()
    proxies_used = maybe_use_proxy(proxies_list)

    w3 = make_web3(rpc, proxies_used)
    try:
        ch_id = w3.eth.chain_id
        console.print(f"Connected. ChainId: [bold]{ch_id}[/bold]")
    except Exception as e:
        console.print(f"[red]RPC error:[/red] {e}")
        return

    compiled = compile_contracts(CONTRACTS_FILE)
    ctx = RunContext(w3=w3, compiled=compiled, proxies_used=proxies_used)

    mode = select_mode()
    dep_count, interactions_per = ask_counts()
    dmin, dmax = ask_delays()

    # Choose contracts set
    if mode == "manual":
        chosen = pick_contracts_manual(compiled)
    else:
        chosen = pick_contracts_random(compiled, dep_count)
    console.print(f"Selected contracts: [bold]{', '.join(chosen)}[/bold]")

    for addr, pk in accounts:
        acct = Account.from_key(pk)
        ctx.stats[addr] = WalletStats()
        console.rule(f"[bold]Wallet {addr}[/bold]")

        deployed_addrs: List[Tuple[str, str]] = []  # (name, address)

        # Deploy loop
        for _ in range(dep_count):
            name = random.choice(chosen) if mode == "random" else random.choice(chosen)
            at = deploy_contract(ctx, acct, name)
            if at:
                ctx.stats[addr].deployed += 1
                deployed_addrs.append((name, at))
            else:
                ctx.stats[addr].failed += 1
            time.sleep(random.uniform(dmin, dmax))

        # Interactions
        for (name, at) in deployed_addrs:
            for _ in range(interactions_per):
                ok = interact_with(ctx, acct, name, at)
                if ok:
                    ctx.stats[addr].interacted += 1
                else:
                    ctx.stats[addr].failed += 1
                time.sleep(random.uniform(dmin, dmax))

    # Summary per wallet
    table = Table(title="Per-Wallet Summary", box=box.SIMPLE_HEAVY)
    table.add_column("Wallet")
    table.add_column("Deployed", justify="right", style="green")
    table.add_column("Interacted", justify="right", style="cyan")
    table.add_column("Failed", justify="right", style="red")

    for w, st in ctx.stats.items():
        table.add_row(w, str(st.deployed), str(st.interacted), str(st.failed))

    console.print(table)
    console.print("[bold green]Done.[/bold green]")

if __name__ == "__main__":
    main()
