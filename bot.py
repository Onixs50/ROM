import os
import json
import random
import time
import requests
from web3 import Web3
from solcx import compile_source, install_solc
import threading
from urllib.parse import urlparse

# ================== NETWORK CONFIG ==================
NETWORK_CONFIG = {
    "chainId": 121214,
    "name": "Martius",
    "rpcUrl": "https://martius-i.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

GAS_LIMIT = 5000000
GAS_PRICE_GWEI = 10

# ================== PROXY CONFIG ==================
class ProxyManager:
    def __init__(self):
        self.online_proxies = []
        self.local_proxies = []
        self.current_proxy = None
        self.proxy_index = 0
        self.failed_proxies = set()
        self.load_local_proxies()
    
    def load_local_proxies(self):
        """Load proxies from proxy.txt file"""
        if os.path.exists("proxy.txt"):
            try:
                with open("proxy.txt", 'r') as f:
                    for line in f:
                        proxy = line.strip()
                        if proxy and not proxy.startswith('#'):
                            if not proxy.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
                                proxy = f"http://{proxy}"
                            self.local_proxies.append(proxy)
                print(f"📁 {len(self.local_proxies)} proxies loaded from proxy.txt")
            except Exception as e:
                print(f"❌ Error loading local proxies: {e}")
        else:
            print("⚠️  proxy.txt not found. Only online proxies will be available.")
    
    def fetch_online_proxies(self):
        """Fetch free proxies from online sources"""
        print("🌐 Fetching online proxies...")
        online_sources = [
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        ]
        
        self.online_proxies = []  # Reset list
        
        for source in online_sources:
            try:
                response = requests.get(source, timeout=15)
                if response.status_code == 200:
                    proxies = response.text.strip().split('\n')
                    for proxy in proxies:
                        proxy = proxy.strip()
                        if ':' in proxy and len(proxy.split(':')) >= 2:
                            if not proxy.startswith(('http://', 'https://', 'socks5://')):
                                formatted_proxy = f"http://{proxy}"
                            else:
                                formatted_proxy = proxy
                            
                            if formatted_proxy not in self.online_proxies and formatted_proxy not in self.failed_proxies:
                                self.online_proxies.append(formatted_proxy)
                                
            except Exception as e:
                print(f"⚠️  Failed to fetch from {source}: {str(e)[:50]}...")
                continue
        
        print(f"✅ {len(self.online_proxies)} online proxies fetched")
    
    def get_working_proxy(self, proxy_type="online"):
        """Get next working proxy"""
        proxy_list = self.online_proxies if proxy_type == "online" else self.local_proxies
        
        # If all proxies failed and we're using local, switch to online
        if not proxy_list or len(self.failed_proxies) >= len(proxy_list):
            if proxy_type == "local":
                print("🔄 All local proxies failed, switching to online proxies...")
                self.fetch_online_proxies()
                proxy_list = self.online_proxies
            else:
                # Refresh online proxies
                print("🔄 Refreshing proxy list...")
                self.failed_proxies.clear()  # Reset failed proxies
                self.fetch_online_proxies()
                proxy_list = self.online_proxies
        
        # Find next working proxy
        attempts = 0
        max_attempts = min(50, len(proxy_list) * 2)  # Try more proxies
        
        while attempts < max_attempts:
            if not proxy_list:
                break
                
            proxy = proxy_list[self.proxy_index % len(proxy_list)]
            self.proxy_index += 1
            attempts += 1
            
            if proxy in self.failed_proxies:
                continue
                
            if self.test_proxy(proxy):
                self.current_proxy = proxy
                return proxy
            else:
                self.failed_proxies.add(proxy)
        
        return None
    
    def test_proxy(self, proxy_url, timeout=10):
        """Test if proxy is working"""
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            response = requests.get(
                "http://httpbin.org/ip", 
                proxies=proxies, 
                timeout=timeout
            )
            return response.status_code == 200
        except:
            return False

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

# ================== GLOBAL VARIABLES ==================
proxy_manager = ProxyManager()
w3 = None
deployed_contracts = []

# ================== WEB3 CONNECTION ==================
def create_web3_connection(use_proxy=False, proxy_type="online", max_retries=10):
    """Create Web3 connection with enhanced retry logic"""
    global w3
    
    if not use_proxy:
        try:
            w3 = Web3(Web3.HTTPProvider(NETWORK_CONFIG["rpcUrl"]))
            if w3.is_connected():
                print("✅ Direct connection established")
                return True
        except:
            pass
        print("❌ Direct connection failed")
        return False
    
    for attempt in range(max_retries):
        try:
            proxy_url = proxy_manager.get_working_proxy(proxy_type)
            
            if not proxy_url:
                if proxy_type == "local":
                    print("🔄 No local proxies available, trying online...")
                    proxy_type = "online"  # Switch to online
                    proxy_url = proxy_manager.get_working_proxy("online")
                
                if not proxy_url:
                    print("❌ No working proxies found")
                    time.sleep(5)
                    continue
            
            print(f"🔄 Attempt {attempt + 1}: Testing proxy {proxy_url[:50]}...")
            
            # Create Web3 with proxy
            session = requests.Session()
            session.proxies.update({'http': proxy_url, 'https': proxy_url})
            session.timeout = 15
            
            w3 = Web3(Web3.HTTPProvider(
                NETWORK_CONFIG["rpcUrl"],
                request_kwargs={'proxies': {'http': proxy_url, 'https': proxy_url}, 'timeout': 30}
            ))
            
            # Test connection
            if w3.is_connected():
                balance_test = w3.eth.get_block('latest')  # More thorough test
                proxy_manager.current_proxy = proxy_url
                print(f"✅ Connected via proxy: {proxy_url[:50]}...")
                return True
                
        except Exception as e:
            print(f"⚠️  Proxy {proxy_url[:30] if 'proxy_url' in locals() else 'unknown'} failed: {str(e)[:50]}...")
            if 'proxy_url' in locals():
                proxy_manager.failed_proxies.add(proxy_url)
            time.sleep(1)
            continue
    
    print(f"❌ Failed to connect after {max_retries} attempts")
    return False

def ensure_connection(use_proxy=False, proxy_type="online"):
    """Ensure Web3 connection with intelligent retry"""
    global w3
    
    # Test current connection
    try:
        if w3 and w3.is_connected():
            # Quick test
            w3.eth.get_block('latest')
            return True
    except:
        pass
    
    print("🔄 Connection lost, reconnecting...")
    return create_web3_connection(use_proxy, proxy_type, max_retries=20)

# ================== LOAD ACCOUNTS ==================
def load_accounts():
    """Load private keys from accounts.txt"""
    private_keys = []
    if not os.path.exists("accounts.txt"):
        raise Exception("❌ accounts.txt not found!")
    
    with open("accounts.txt") as f:
        for line in f:
            key = line.strip().lower()
            if key.startswith("0x"):
                key = key[2:]
            if len(key) == 64 and all(c in "0123456789abcdef" for c in key):
                private_keys.append("0x" + key)
    
    if not private_keys:
        raise Exception("❌ No valid private keys found in accounts.txt")
    
    return private_keys

# ================== UTILITIES ==================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def get_balance(address):
    """Get balance with retry logic"""
    for attempt in range(3):
        try:
            return w3.eth.get_balance(address)
        except Exception as e:
            if attempt < 2:
                print(f"⚠️  Error getting balance, retrying... ({attempt + 1}/3)")
                time.sleep(1)
            else:
                print(f"❌ Failed to get balance: {e}")
                return 0

def get_nonce(address):
    """Get nonce with retry logic"""
    for attempt in range(3):
        try:
            return w3.eth.get_transaction_count(address, "pending")
        except Exception as e:
            if attempt < 2:
                print(f"⚠️  Error getting nonce, retrying... ({attempt + 1}/3)")
                time.sleep(1)
            else:
                print(f"❌ Failed to get nonce: {e}")
                return 0

def wait_for_balance(address, min_balance_wei=1000000000000000):  # 0.001 ETH
    """Wait for sufficient balance"""
    while True:
        try:
            current_balance = get_balance(address)
            if current_balance >= min_balance_wei:
                return current_balance
            
            balance_eth = w3.from_wei(current_balance, 'ether')
            min_balance_eth = w3.from_wei(min_balance_wei, 'ether')
            
            print(f"💰 Insufficient balance: {balance_eth:.6f} {NETWORK_CONFIG['currency']}")
            print(f"   Required: {min_balance_eth:.6f} {NETWORK_CONFIG['currency']}")
            print("   Please add funds to continue...")
            
            time.sleep(10)  # Wait 10 seconds before checking again
            
        except Exception as e:
            print(f"⚠️  Error checking balance: {e}")
            time.sleep(5)

def report_tx(receipt, operation="Transaction", show_balance=True):
    """Report transaction details"""
    print(f"✅ {operation} confirmed")
    print(f"📝 TxHash: {receipt.transactionHash.hex()}")
    print(f"⛽ Gas Used: {receipt.gasUsed:,}")
    
    if operation.startswith("Deploy") and hasattr(receipt, 'contractAddress'):
        print(f"📍 Contract: {receipt.contractAddress}")
    
    if show_balance:
        try:
            private_keys = load_accounts()
            account = w3.eth.account.from_key(private_keys[0])
            balance = get_balance(account.address)
            print(f"💰 Balance: {w3.from_wei(balance, 'ether'):.6f} {NETWORK_CONFIG['currency']}")
        except:
            pass
            
    print("─" * 60)

# ================== COMPILE CONTRACT ==================
def compile_contract(source_code, contract_name):
    """Compile Solidity contract"""
    try:
        install_solc("0.8.20")
        compiled = compile_source(source_code, output_values=["abi", "bin"], solc_version="0.8.20")
        contract_interface = compiled[f"<stdin>:{contract_name}"]
        return contract_interface["abi"], contract_interface["bin"]
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        raise

# ================== DEPLOY WITH PERSISTENCE ==================
def deploy_contract_persistent(abi, bytecode, account, contract_name, use_proxy=False, proxy_type="online"):
    """Deploy contract with infinite retry until success"""
    attempt = 0
    
    while True:
        attempt += 1
        try:
            # Ensure connection
            if not ensure_connection(use_proxy, proxy_type):
                print(f"⚠️  Connection failed on attempt {attempt}, retrying in 5 seconds...")
                time.sleep(5)
                continue
            
            # Wait for sufficient balance
            wait_for_balance(account.address)
            
            contract = w3.eth.contract(abi=abi, bytecode=bytecode)
            nonce = get_nonce(account.address)
            
            if nonce == 0:  # Nonce error
                print("⚠️  Invalid nonce, reconnecting...")
                if use_proxy:
                    create_web3_connection(use_proxy, proxy_type)
                time.sleep(2)
                continue
            
            tx = contract.constructor().build_transaction({
                "from": account.address,
                "gas": GAS_LIMIT,
                "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
                "nonce": nonce,
                "chainId": NETWORK_CONFIG["chainId"]
            })
            
            signed = w3.eth.account.sign_transaction(tx, account.key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"🔄 Waiting for {contract_name} deployment confirmation...")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            return receipt
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Deploy attempt {attempt} failed: {error_msg[:100]}...")
            
            # Handle specific errors
            if "insufficient funds" in error_msg.lower():
                print("💰 Insufficient funds detected, waiting for balance...")
                wait_for_balance(account.address)
                continue
            
            if "nonce" in error_msg.lower() or "already known" in error_msg.lower():
                print("🔄 Nonce issue, waiting and retrying...")
                time.sleep(5)
                continue
            
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                print("🔄 Connection issue, switching proxy...")
                if use_proxy:
                    create_web3_connection(use_proxy, proxy_type)
                time.sleep(3)
                continue
            
            # Generic retry with delay
            wait_time = min(30, attempt * 2)  # Exponential backoff, max 30s
            print(f"🔄 Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

def interact_contract_persistent(contract_address, contract_type, account, use_proxy=False, proxy_type="online"):
    """Interact with contract with infinite retry until success"""
    attempt = 0
    
    while True:
        attempt += 1
        try:
            # Ensure connection
            if not ensure_connection(use_proxy, proxy_type):
                print(f"⚠️  Connection failed on attempt {attempt}, retrying in 5 seconds...")
                time.sleep(5)
                continue
            
            # Wait for sufficient balance
            wait_for_balance(account.address)
            
            if contract_type == "storage":
                abi, _ = compile_contract(STORAGE_SOURCE, "Storage")
                contract = w3.eth.contract(address=contract_address, abi=abi)
                value = random.randint(1, 1000)
                
                tx = contract.functions.set(value).build_transaction({
                    "from": account.address,
                    "gas": GAS_LIMIT,
                    "gasPrice": w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                    "nonce": get_nonce(account.address),
                    "chainId": NETWORK_CONFIG["chainId"]
                })
                
                operation_desc = f"Storage.set({value})"
                
            elif contract_type == "counter":
                abi, _ = compile_contract(COUNTER_SOURCE, "Counter")
                contract = w3.eth.contract(address=contract_address, abi=abi)
                increment = random.randint(1, 50)
                
                tx = contract.functions.increment(increment).build_transaction({
                    "from": account.address,
                    "gas": GAS_LIMIT,
                    "gasPrice": w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                    "nonce": get_nonce(account.address),
                    "chainId": NETWORK_CONFIG["chainId"]
                })
                
                operation_desc = f"Counter.increment({increment})"
            
            signed = w3.eth.account.sign_transaction(tx, account.key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            print(f"📝 {operation_desc}")
            return receipt
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Interaction attempt {attempt} failed: {error_msg[:100]}...")
            
            # Handle specific errors (same logic as deploy)
            if "insufficient funds" in error_msg.lower():
                print("💰 Insufficient funds detected, waiting for balance...")
                wait_for_balance(account.address)
                continue
            
            if "nonce" in error_msg.lower():
                print("🔄 Nonce issue, waiting and retrying...")
                time.sleep(5)
                continue
            
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                print("🔄 Connection issue, switching proxy...")
                if use_proxy:
                    create_web3_connection(use_proxy, proxy_type)
                time.sleep(3)
                continue
            
            wait_time = min(30, attempt * 2)
            print(f"🔄 Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

# ================== AUTOMATED WORKFLOW ==================
def automated_workflow():
    """Complete automated workflow: Deploy + Interact"""
    clear()
    print("🤖 AUTOMATED DEPLOYMENT & INTERACTION WORKFLOW")
    print("=" * 60)
    
    try:
        # Get user inputs
        contract_count = int(input("🏗️  How many contract pairs to deploy? "))
        interaction_count = int(input("⚡ How many interactions to perform? "))
        
        print("\n📡 Connection Options:")
        print("1. Direct connection (no proxy)")
        print("2. Use proxy")
        
        connection_choice = input("Select (1-2): ").strip()
        use_proxy = connection_choice == "2"
        proxy_type = "online"
        
        if use_proxy:
            print("\n🌐 Proxy Options:")
            print("1. Online proxies (recommended)")
            print("2. Local proxies (proxy.txt)")
            proxy_choice = input("Select (1-2): ").strip()
            proxy_type = "online" if proxy_choice == "1" else "local"
        
        # Establish initial connection
        print("\n🔌 Establishing connection...")
        if not create_web3_connection(use_proxy, proxy_type):
            print("❌ Failed to establish initial connection")
            return
        
        private_keys = load_accounts()
        account = w3.eth.account.from_key(private_keys[0])
        
        print(f"\n🚀 Starting automated workflow:")
        print(f"   📦 {contract_count} contract pairs to deploy")
        print(f"   ⚡ {interaction_count} interactions to perform")
        print(f"   📍 Account: {account.address}")
        
        input("\n📌 Press Enter to start...")
        clear()
        
        # Phase 1: Deployment
        print("🏗️  PHASE 1: CONTRACT DEPLOYMENT")
        print("=" * 40)
        
        deployed_contracts.clear()  # Reset
        
        for i in range(contract_count):
            pair_num = i + 1
            print(f"\n📦 Deploying contract pair {pair_num}/{contract_count}")
            
            # Deploy Storage
            print(f"   🏗️  [{pair_num}.1] Deploying Storage contract...")
            try:
                storage_abi, storage_bin = compile_contract(STORAGE_SOURCE, "Storage")
                receipt = deploy_contract_persistent(storage_abi, storage_bin, account, "Storage", use_proxy, proxy_type)
                deployed_contracts.append({"name": "storage", "address": receipt.contractAddress})
                report_tx(receipt, f"Deploy Storage #{pair_num}")
            except KeyboardInterrupt:
                print("\n⚠️  Deployment interrupted by user")
                return
            
            # Deploy Counter
            print(f"   🏗️  [{pair_num}.2] Deploying Counter contract...")
            try:
                counter_abi, counter_bin = compile_contract(COUNTER_SOURCE, "Counter")
                receipt = deploy_contract_persistent(counter_abi, counter_bin, account, "Counter", use_proxy, proxy_type)
                deployed_contracts.append({"name": "counter", "address": receipt.contractAddress})
                report_tx(receipt, f"Deploy Counter #{pair_num}")
            except KeyboardInterrupt:
                print("\n⚠️  Deployment interrupted by user")
                return
            
            # Small delay between pairs
            time.sleep(random.uniform(1, 3))
        
        print(f"\n✅ DEPLOYMENT COMPLETED: {len(deployed_contracts)} contracts deployed")
        
        # Phase 2: Interactions
        print(f"\n⚡ PHASE 2: CONTRACT INTERACTIONS")
        print("=" * 40)
        print(f"Target: {interaction_count} interactions")
        
        interactions_completed = 0
        
        while interactions_completed < interaction_count:
            try:
                for contract_info in deployed_contracts:
                    if interactions_completed >= interaction_count:
                        break
                    
                    interactions_completed += 1
                    progress = (interactions_completed / interaction_count) * 100
                    
                    print(f"\n⚡ [{interactions_completed}/{interaction_count}] ({progress:.1f}%) Interacting with {contract_info['name']}...")
                    
                    receipt = interact_contract_persistent(
                        contract_info['address'],
                        contract_info['name'],
                        account,
                        use_proxy,
                        proxy_type
                    )
                    
                    report_tx(receipt, f"Interact {contract_info['name'].title()}", show_balance=(interactions_completed % 10 == 0))
                    
                    # Small delay
                    time.sleep(random.uniform(0.5, 2))
                    
            except KeyboardInterrupt:
                print(f"\n⚠️  Interactions interrupted by user at {interactions_completed}/{interaction_count}")
                break
        
        # Final Summary
        print(f"\n🎉 WORKFLOW COMPLETED!")
        print("=" * 40)
        print(f"✅ Contracts Deployed: {len(deployed_contracts)}")
        print(f"✅ Interactions Completed: {interactions_completed}/{interaction_count}")
        
        if interactions_completed >= interaction_count:
            print("🏆 All targets achieved successfully!")
        else:
            print(f"⚠️  Partial completion: {interactions_completed}/{interaction_count} interactions")
        
    except KeyboardInterrupt:
        print("\n\n👋 Workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Workflow error: {e}")

# ================== MENU FUNCTIONS ==================
def show_status():
    """Show current status"""
    try:
        private_keys = load_accounts()
        account = w3.eth.account.from_key(private_keys[0])
        
        if not w3 or not w3.is_connected():
            print("❌ No active connection")
            return
            
        balance = get_balance(account.address)
        tx_count = get_nonce(account.address)
        
        print("┌─────────────────────────────────────┐")
        print("│           ACCOUNT STATUS            │")
        print("├─────────────────────────────────────┤")
        print(f"│ Address: {account.address[:20]}... │")
        print(f"│ Balance: {w3.from_wei(balance, 'ether'):.6f} {NETWORK_CONFIG['currency']:<9} │")
        print(f"│ Tx Count: {tx_count:<22} │")
        print(f"│ Network: {NETWORK_CONFIG['name']:<22} │")
        if proxy_manager.current_proxy:
            print(f"│ Proxy: {proxy_manager.current_proxy[:25]:<25} │")
        else:
            print(f"│ Connection: Direct{'':15} │")
        print(f"│ Contracts: {len(deployed_contracts):<20} │")
        print("└─────────────────────────────────────┘")
        
    except Exception as e:
        print(f"❌ Error showing status: {e}")

def show_contracts():
    """Show deployed contracts"""
    if not deployed_contracts:
        print("❌ No deployed contracts found.")
        return
    
    print("┌─────────────────────────────────────────────────────────┐")
    print("│                 DEPLOYED CONTRACTS                      │")
    print("├─────────────────────────────────────────────────────────┤")
    
    for i, contract in enumerate(deployed_contracts):
        contract_type = contract['name'].upper()
        address = contract['address']
        print(f"│ {i+1:2}. {contract_type:<8} │ {address} │")
    
    print("└─────────────────────────────────────────────────────────┘")

# ================== MAIN ==================
def main():
    """Main application"""
    global deployed_contracts
    
    try:
        clear()
        print("🚀 BLOCKCHAIN AUTOMATION TOOL v2.0")
        print("🔥 Enhanced with Persistent Retry & Auto Proxy Switching")
        print("=" * 60)
        
        while True:
            print("\n┌─────────────────────────────────────┐")
            print("│              MAIN MENU              │")
            print("├─────────────────────────────────────┤")
            print("│ 1. 📊 Show Account Status           │")
            print("│ 2. 🤖 Automated Deploy & Interact   │")
            print("│ 3. 🏗️  Manual Deploy Contracts      │")
            print("│ 4. ⚡ Manual Interact with Contracts│")
            print("│ 5. 📋 Show Deployed Contracts       │")
            print("│ 0. 🚪 Exit                          │")
            print("└─────────────────────────────────────┘")
            
            choice = input("\n🎯 Select option: ").strip()
            
            if choice == "1":
                clear()
                show_status()
                input("\n📌 Press Enter to continue...")
                clear()
                
            elif choice == "2":
                automated_workflow()
                input("\n📌 Press Enter to continue...")
                clear()
                
            elif choice == "3":
                clear()
                print("🏗️  Manual deployment feature available")
                print("💡 Tip: Use option 2 for automated deployment")
                input("\n📌 Press Enter to continue...")
                clear()
                
            elif choice == "4":
                clear()
                if not deployed_contracts:
                    print("❌ No deployed contracts. Use option 2 to deploy first.")
                else:
                    print("⚡ Manual interaction feature available")
                    print("💡 Tip: Use option 2 for automated interaction")
                input("\n📌 Press Enter to continue...")
                clear()
                
            elif choice == "5":
                clear()
                show_contracts()
                input("\n📌 Press Enter to continue...")
                clear()
                
            elif choice == "0":
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice! Please select 0-5")
                time.sleep(1)
                clear()
                
    except KeyboardInterrupt:
        print("\n\n👋 Application interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Application error: {e}")

if __name__ == "__main__":
    main()
