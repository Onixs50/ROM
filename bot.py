import os
import json
import random
import time
from web3 import Web3
from solcx import compile_source, install_solc

# ================== NETWORK CONFIG ==================
NETWORK_CONFIG = {
    "chainId": 121214,
    "name": "Martius",
    "rpcUrl": "https://martius-i.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

GAS_LIMIT = 5000000
GAS_PRICE_GWEI = 10  # gwei
MIN_SEND_AMOUNT = 0.00001  # rSOL

# ================== CONTRACT SOURCES ==================
STORAGE_SOURCE = '''
pragma solidity ^0.8.0;
contract Storage {
    uint256 private value;
    function set(uint256 _value) public { value = _value; }
    function get() public view returns (uint256) { return value; }
}
'''

COUNTER_SOURCE = '''
pragma solidity ^0.8.0;
contract Counter {
    uint256 private count;
    function increment(uint256 amount) public { count += amount; }
    function get() public view returns (uint256) { return count; }
}
'''

# ================== INIT WEB3 ==================
w3 = Web3(Web3.HTTPProvider(NETWORK_CONFIG["rpcUrl"]))
if not w3.is_connected():
    raise Exception("Failed to connect to Martius RPC")

# ================== LOAD ACCOUNTS ==================
private_keys = []
if not os.path.exists("accounts.txt"):
    raise Exception("accounts.txt not found!")
with open("accounts.txt") as f:
    for line in f:
        key = line.strip().lower()
        if key.startswith("0x"):
            key = key[2:]
        if len(key) == 64 and all(c in "0123456789abcdef" for c in key):
            private_keys.append("0x" + key)
if not private_keys:
    raise Exception("No valid private keys found in accounts.txt")

PRIVATE_KEY = private_keys[0]
account = w3.eth.account.from_key(PRIVATE_KEY)
ADDRESS = account.address

# ================== UTILITIES ==================
def clear(): os.system("cls" if os.name=="nt" else "clear")
def get_balance(): return w3.eth.get_balance(ADDRESS)
def get_nonce(): return w3.eth.get_transaction_count(ADDRESS, "pending")
def report_tx(receipt):
    print("✅ Transaction confirmed")
    print(f"TxHash: {receipt.transactionHash.hex()}")
    print(f"Gas Used: {receipt.gasUsed}")
    print(f"Explorer: {NETWORK_CONFIG['explorer']}/tx/{receipt.transactionHash.hex()}")
    print(f"Balance: {w3.from_wei(get_balance(),'ether')} {NETWORK_CONFIG['currency']}")
    print("--------------------------------------------------")

# ================== COMPILE CONTRACT ==================
def compile_contract(source_code, contract_name):
    install_solc("0.8.20")
    compiled = compile_source(source_code, output_values=["abi","bin"], solc_version="0.8.20")
    contract_interface = compiled[f"<stdin>:{contract_name}"]
    return contract_interface["abi"], contract_interface["bin"]

# ================== DEPLOY CONTRACT ==================
def deploy_contract(abi, bytecode):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor().build_transaction({
        "from": ADDRESS,
        "gas": GAS_LIMIT,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "nonce": get_nonce(),
        "chainId": NETWORK_CONFIG["chainId"]
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

# ================== INTERACTIONS ==================
def interact_storage(address):
    abi, _ = compile_contract(STORAGE_SOURCE, "Storage")
    contract = w3.eth.contract(address=address, abi=abi)
    value = random.randint(1, 100)
    tx = contract.functions.set(value).build_transaction({
        "from": ADDRESS,
        "gas": GAS_LIMIT,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
        "nonce": get_nonce(),
        "chainId": NETWORK_CONFIG["chainId"]
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Storage set value: {value}")
    report_tx(receipt)

def interact_counter(address):
    abi, _ = compile_contract(COUNTER_SOURCE, "Counter")
    contract = w3.eth.contract(address=address, abi=abi)
    increment = random.randint(1, 10)
    tx = contract.functions.increment(increment).build_transaction({
        "from": ADDRESS,
        "gas": GAS_LIMIT,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
        "nonce": get_nonce(),
        "chainId": NETWORK_CONFIG["chainId"]
    })
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Counter incremented by: {increment}")
    report_tx(receipt)

# ================== SEND TOKENS ==================
def send_tokens(targets, max_amount):
    nonce = get_nonce()
    for target in targets:
        amount = random.uniform(MIN_SEND_AMOUNT, max_amount)
        tx = {
            "from": ADDRESS,
            "to": target,
            "value": w3.to_wei(amount, 'ether'),
            "gas": 21000,
            "gasPrice": w3.to_wei(GAS_PRICE_GWEI,'gwei'),
            "nonce": nonce,
            "chainId": NETWORK_CONFIG["chainId"]
        }
        try:
            signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Sent {amount:.6f} {NETWORK_CONFIG['currency']} to {target}")
            report_tx(receipt)
            nonce += 1
            time.sleep(random.uniform(0.5,1.5))
        except Exception as e:
            print(f"⚠️ Failed to send to {target}: {e}")
            nonce += 1

# ================== MAIN ==================
def main():
    deployed_contracts = []
    while True:
        clear()
        print("===== MENU =====")
        print("1. Show balance & tx count")
        print("2. Deploy contracts")
        print("3. Interact with contracts")
        print("4. Send tokens random")
        print("5. Send tokens specific wallet")
        print("0. Exit")
        choice = input("Select: ")
        if choice=="1":
            print(f"💰 Balance: {w3.from_wei(get_balance(),'ether')} {NETWORK_CONFIG['currency']}")
            print(f"🔢 Tx count: {get_nonce()}")
            input("Enter...")
        elif choice=="2":
            times=int(input("How many times to deploy Storage+Counter? "))
            for i in range(times):
                storage_abi, storage_bin = compile_contract(STORAGE_SOURCE,"Storage")
                counter_abi, counter_bin = compile_contract(COUNTER_SOURCE,"Counter")
                print(f"Deploying Storage #{i+1}...")
                receipt = deploy_contract(storage_abi, storage_bin)
                deployed_contracts.append({"name":"storage","address":receipt.contractAddress})
                report_tx(receipt)
                print(f"Deploying Counter #{i+1}...")
                receipt = deploy_contract(counter_abi, counter_bin)
                deployed_contracts.append({"name":"counter","address":receipt.contractAddress})
                report_tx(receipt)
            input("Enter...")
        elif choice=="3":
            rounds=int(input("How many interaction rounds? "))
            for r in range(rounds):
                print(f"--- Interaction round {r+1} ---")
                for c in deployed_contracts:
                    print(f"Interacting with {c['name']} at {c['address']}")
                    if c["name"]=="storage":
                        interact_storage(c['address'])
                    elif c["name"]=="counter":
                        interact_counter(c['address'])
                    time.sleep(1)
            input("Enter...")
        elif choice=="4":
            count=int(input("Random wallets: "))
            max_amount=float(input("Max amount: "))
            wallets=[w3.eth.account.create().address for _ in range(count)]
            send_tokens(wallets,max_amount)
            input("Enter...")
        elif choice=="5":
            target=input("Wallet: ").strip()
            amount=float(input("Amount: "))
            send_tokens([target],amount)
            input("Enter...")
        elif choice=="0":
            break
        else:
            input("Invalid choice, Enter...")

if __name__=="__main__":
    main()
