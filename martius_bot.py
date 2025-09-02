#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from web3 import Web3
from eth_account import Account
import requests
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# Import contracts
try:
    from contracts import CONTRACTS
except ImportError:
    print(f"{Fore.RED}contracts.py file not found! Please ensure contracts.py is in the same directory.{Style.RESET_ALL}")
    sys.exit(1)

# Network Configuration
NETWORK_CONFIG = {
    "name": "Martius",
    "chain_id": 121214,
    "rpc_url": "https://martius-ii.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

class ProxyManager:
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.load_proxies()
    
    def load_proxies(self):
        try:
            if not os.path.exists(self.proxy_file):
                with open(self.proxy_file, "w") as f:
                    f.write("# Add your proxies here (one per line)\n")
                    f.write("# Format: ip:port or ip:port:user:pass or user:pass@ip:port\n")
                return
            
            with open(self.proxy_file, 'r') as f:
                lines = f.read().strip().split('\n')
            
            for line in lines:
                if not line.strip() or line.startswith('#'):
                    continue
                
                proxy = self.parse_proxy(line.strip())
                if proxy:
                    self.proxies.append(proxy)
            
            if self.proxies:
                print(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading proxies: {e}{Style.RESET_ALL}")
    
    def parse_proxy(self, line: str) -> Optional[Dict]:
        try:
            if '@' in line:
                auth, address = line.split('@')
                user, password = auth.split(':')
                ip, port = address.split(':')
            elif line.count(':') == 3:
                ip, port, user, password = line.split(':')
            elif line.count(':') == 1:
                ip, port = line.split(':')
                user = password = None
            else:
                return None
            
            proxy_dict = {
                'http': f'http://{ip}:{port}',
                'https': f'http://{ip}:{port}'
            }
            
            if user and password:
                proxy_dict['http'] = f'http://{user}:{password}@{ip}:{port}'
                proxy_dict['https'] = f'http://{user}:{password}@{ip}:{port}'
            
            return proxy_dict
        except:
            return None
    
    def get_random_proxy(self) -> Optional[Dict]:
        return random.choice(self.proxies) if self.proxies else None

class MartianBot:
    def __init__(self):
        # Initialize with default settings
        self.session = requests.Session()
        self.proxy_manager = ProxyManager()
        self.current_proxy = None
        
        # Setup proxy if available
        if self.proxy_manager.proxies:
            self.current_proxy = self.proxy_manager.get_random_proxy()
            self.session.proxies = self.current_proxy
        
        # Initialize Web3 with custom session
        self.w3 = Web3(Web3.HTTPProvider(
            NETWORK_CONFIG["rpc_url"],
            session=self.session
        ))
        
        self.accounts = []
        self.deployed_contracts = {}
        self.stats = {
            "total_deployments": 0,
            "successful_deployments": 0,
            "total_interactions": 0,
            "successful_interactions": 0,
            "total_transfers": 0,
            "successful_transfers": 0
        }
        
        # Create required files and load accounts
        self.create_files_if_not_exist()
        self.load_accounts()
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def create_files_if_not_exist(self):
        if not os.path.exists("accounts.txt"):
            with open("accounts.txt", "w") as f:
                f.write("# Add your private keys here (one per line)\n")
                f.write("# Example: 0x1234567890abcdef...\n")
            print(f"{Fore.YELLOW}Created accounts.txt - Please add your private keys{Style.RESET_ALL}")
        
        if not os.path.exists("deployed_contracts.json"):
            with open("deployed_contracts.json", "w") as f:
                json.dump({}, f)
        
        try:
            with open("deployed_contracts.json", "r") as f:
                self.deployed_contracts = json.load(f)
        except:
            self.deployed_contracts = {}
    
    def save_deployed_contracts(self):
        try:
            with open("deployed_contracts.json", "w") as f:
                json.dump(self.deployed_contracts, f, indent=2)
        except Exception as e:
            print(f"{Fore.RED}Error saving contracts: {e}{Style.RESET_ALL}")
    
    def load_accounts(self):
        try:
            if not os.path.exists("accounts.txt"):
                return
            
            with open("accounts.txt", 'r') as f:
                lines = f.read().strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                private_key = line
                if not private_key.startswith('0x'):
                    private_key = '0x' + private_key
                
                try:
                    account = Account.from_key(private_key)
                    self.accounts.append({
                        'private_key': private_key,
                        'address': account.address,
                        'account': account
                    })
                except Exception:
                    continue
            
            print(f"{Fore.GREEN}Loaded {len(self.accounts)} accounts{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading accounts: {e}{Style.RESET_ALL}")
    
    def rotate_proxy(self):
        """Rotate to next proxy"""
        if self.proxy_manager.proxies:
            self.current_proxy = self.proxy_manager.get_random_proxy()
            self.session.proxies = self.current_proxy
            
            # Recreate Web3 instance with new proxy
            self.w3 = Web3(Web3.HTTPProvider(
                NETWORK_CONFIG["rpc_url"],
                session=self.session
            ))
    
    def print_banner(self):
        proxy_status = f"Proxy: {len(self.proxy_manager.proxies)} loaded" if self.proxy_manager.proxies else "Proxy: Not used"
        
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    🚀 MARTIUS NETWORK BOT 🚀                  ║
║                       Advanced Version 2.0                   ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}Network: {NETWORK_CONFIG['name']} | Chain ID: {NETWORK_CONFIG['chain_id']}
Currency: {NETWORK_CONFIG['currency']}
Accounts: {len(self.accounts)} | {proxy_status}{Style.RESET_ALL}
        """
        print(banner)
    
    def print_stats(self):
        print(f"""
{Fore.CYAN}📊 STATISTICS:{Style.RESET_ALL}
{Fore.WHITE}Deployments: {self.stats['successful_deployments']}/{self.stats['total_deployments']}
Interactions: {self.stats['successful_interactions']}/{self.stats['total_interactions']}
Transfers: {self.stats['successful_transfers']}/{self.stats['total_transfers']}{Style.RESET_ALL}
        """)
    
    def print_menu(self):
        menu = f"""
{Fore.CYAN}╔═══════════════ MAIN MENU ═══════════════╗{Style.RESET_ALL}
{Fore.WHITE}║  1. 🚀 Deploy Contracts                 ║
║  2. 🔗 Interact with Contracts          ║
║  3. 💸 Send Random Transfers            ║
║  4. 📊 View Statistics                  ║
║  5. 🎲 Random Operations (All in One)   ║
║  6. 🔧 Settings                         ║
║  7. 🚪 Exit                             ║{Style.RESET_ALL}
{Fore.CYAN}╚═════════════════════════════════════════╝{Style.RESET_ALL}
        """
        print(menu)
    
    async def get_balance(self, address: str) -> float:
        try:
            # Add retry logic with proxy rotation
            for attempt in range(3):
                try:
                    balance_wei = self.w3.eth.get_balance(address)
                    return float(self.w3.from_wei(balance_wei, 'ether'))
                except Exception as e:
                    if attempt < 2:
                        self.rotate_proxy()
                        await asyncio.sleep(1)
                        continue
                    raise e
        except:
            return 0.0
    
    def build_transaction_params(self, account: Dict, **kwargs) -> Dict:
        """Build proper transaction parameters for Martius network"""
        # Get current network status
        try:
            nonce = self.w3.eth.get_transaction_count(account['address'])
            gas_price = self.w3.eth.gas_price
        except Exception:
            # Fallback values
            nonce = 0
            gas_price = self.w3.to_wei(20, 'gwei')
        
        # Base transaction parameters
        params = {
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': NETWORK_CONFIG["chain_id"]
        }
        
        # Merge with provided kwargs
        params.update(kwargs)
        
        return params
    
    async def deploy_contract(self, account: Dict, contract_key: str) -> Dict:
        try:
            contract_info = CONTRACTS[contract_key]
            print(f"    📋 Contract: {contract_key}")
            print(f"    🔧 Preparing deployment...")
            
            # Use a working bytecode for simple storage contract
            # This bytecode creates a simple storage contract that works
            working_bytecode = (
                "0x608060405234801561001057600080fd5b5060f78061001f6000396000f3fe6080604052348015600f57600080fd5b506004361060325760003560e01c80632e64cec11460375780636057361d14604f575b600080fd5b60005460405190815260200160405180910390f35b60596004803603602081101560635760008081fd5b5035600055005b600080fdfea264697066735822122084d2f1e6b5c7c8a5f0b5c3a4b8d6e0a2c9b8e4f7d3c6e2a1f4b3c8d5e7a6b9c364736f6c634300060c0033"
            )
            
            # Build transaction
            transaction = self.build_transaction_params(
                account,
                gas=500000,
                data=working_bytecode,
                value=0
            )
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            
            # Send transaction with retry logic
            tx_hash = None
            for attempt in range(3):
                try:
                    # Use raw_transaction (new Web3 versions) or rawTransaction (old versions)
                    raw_tx = getattr(signed_txn, 'raw_transaction', 
                                   getattr(signed_txn, 'rawTransaction', None))
                    
                    if raw_tx is None:
                        return {'success': False, 'error': 'Could not get raw transaction'}
                    
                    tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"    ⚠️  Attempt {attempt + 1} failed, retrying...")
                        self.rotate_proxy()
                        await asyncio.sleep(2)
                        continue
                    return {'success': False, 'error': str(e)}
            
            print(f"    ⏳ Waiting for confirmation...")
            
            # Wait for receipt with retry
            receipt = None
            for attempt in range(5):
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                    break
                except Exception:
                    if attempt < 4:
                        await asyncio.sleep(5)
                        continue
                    return {'success': False, 'error': 'Transaction timeout'}
            
            self.stats['total_deployments'] += 1
            
            if receipt and receipt.status == 1:
                contract_address = receipt.contractAddress
                
                # Save deployment
                if account['address'] not in self.deployed_contracts:
                    self.deployed_contracts[account['address']] = []
                
                self.deployed_contracts[account['address']].append({
                    'type': contract_key,
                    'name': contract_info['name'],
                    'address': contract_address,
                    'tx_hash': tx_hash.hex(),
                    'deployed_at': datetime.now().isoformat()
                })
                
                self.save_deployed_contracts()
                self.stats['successful_deployments'] += 1
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'contract_address': contract_address,
                    'gas_used': receipt.gasUsed
                }
            else:
                return {'success': False, 'error': 'Transaction failed'}
                
        except Exception as e:
            self.stats['total_deployments'] += 1
            return {'success': False, 'error': str(e)}
    
    async def send_random_transfer(self, account: Dict, min_amount: float, max_amount: float) -> Dict:
        try:
            # Generate valid random recipient (checksum address)
            random_bytes = os.urandom(20)
            random_recipient = self.w3.to_checksum_address(random_bytes.hex())
            
            # Random amount
            amount = random.uniform(min_amount, max_amount)
            amount_wei = self.w3.to_wei(amount, 'ether')
            
            # Check balance
            balance = await self.get_balance(account['address'])
            if balance < (amount + 0.005):  # Keep some for gas
                return {'success': False, 'error': f'Insufficient balance: {balance:.4f} rSOL'}
            
            # Build transaction
            transaction = self.build_transaction_params(
                account,
                to=random_recipient,
                value=amount_wei,
                gas=21000
            )
            
            # Sign and send
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            
            # Send with retry logic
            for attempt in range(3):
                try:
                    raw_tx = getattr(signed_txn, 'raw_transaction', 
                                   getattr(signed_txn, 'rawTransaction', None))
                    
                    if raw_tx is None:
                        return {'success': False, 'error': 'Could not get raw transaction'}
                    
                    tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                    break
                except Exception as e:
                    if attempt < 2:
                        self.rotate_proxy()
                        await asyncio.sleep(1)
                        continue
                    return {'success': False, 'error': str(e)}
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            self.stats['total_transfers'] += 1
            
            if receipt.status == 1:
                self.stats['successful_transfers'] += 1
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'amount': amount,
                    'recipient': random_recipient,
                    'gas_used': receipt.gasUsed
                }
            else:
                return {'success': False, 'error': 'Transaction failed'}
                
        except Exception as e:
            self.stats['total_transfers'] += 1
            return {'success': False, 'error': str(e)}
    
    async def deploy_contracts_menu(self):
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🚀 CONTRACT DEPLOYMENT{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Available Contracts:{Style.RESET_ALL}")
        
        contract_list = list(CONTRACTS.keys())
        for i, contract_key in enumerate(contract_list, 1):
            print(f"{Fore.WHITE}{i}. {CONTRACTS[contract_key]['name']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{len(contract_list)+1}. Random Selection{Style.RESET_ALL}")
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select contract (1-{len(contract_list)+1}): {Style.RESET_ALL}")
            
            if choice == str(len(contract_list)+1):
                num_deployments = int(input(f"{Fore.YELLOW}Deployments per account: {Style.RESET_ALL}"))
                min_delay = float(input(f"{Fore.YELLOW}Min delay (seconds): {Style.RESET_ALL}"))
                max_delay = float(input(f"{Fore.YELLOW}Max delay (seconds): {Style.RESET_ALL}"))
                
                for account in self.accounts:
                    print(f"\n{Fore.BLUE}Processing: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                    balance = await self.get_balance(account['address'])
                    print(f"  💰 Balance: {balance:.4f} rSOL")
                    
                    if balance < 0.01:
                        print(f"  {Fore.RED}⚠️  Low balance - skipping{Style.RESET_ALL}")
                        continue
                    
                    for i in range(num_deployments):
                        contract_key = random.choice(contract_list)
                        print(f"  [{i+1}/{num_deployments}] Deploying {CONTRACTS[contract_key]['name']}...")
                        
                        result = await self.deploy_contract(account, contract_key)
                        
                        if result['success']:
                            print(f"  {Fore.GREEN}✅ Success: {result['contract_address']}{Style.RESET_ALL}")
                            print(f"  {Fore.GREEN}   TX: {result['tx_hash']}{Style.RESET_ALL}")
                        else:
                            print(f"  {Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")
                        
                        if i < num_deployments - 1:
                            delay = random.uniform(min_delay, max_delay)
                            print(f"  ⏳ Waiting {delay:.1f}s...")
                            await asyncio.sleep(delay)
            
            else:
                contract_index = int(choice) - 1
                if 0 <= contract_index < len(contract_list):
                    contract_key = contract_list[contract_index]
                    
                    for account in self.accounts:
                        print(f"\n{Fore.BLUE}Deploying for: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                        
                        result = await self.deploy_contract(account, contract_key)
                        
                        if result['success']:
                            print(f"{Fore.GREEN}✅ Success: {result['contract_address']}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")
                            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def send_transfers_menu(self):
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}💸 RANDOM TRANSFERS{Style.RESET_ALL}")
        
        try:
            min_amount = float(input(f"{Fore.YELLOW}Min transfer amount (rSOL): {Style.RESET_ALL}"))
            max_amount = float(input(f"{Fore.YELLOW}Max transfer amount (rSOL): {Style.RESET_ALL}"))
            num_transfers = int(input(f"{Fore.YELLOW}Transfers per account: {Style.RESET_ALL}"))
            min_delay = float(input(f"{Fore.YELLOW}Min delay (seconds): {Style.RESET_ALL}"))
            max_delay = float(input(f"{Fore.YELLOW}Max delay (seconds): {Style.RESET_ALL}"))
            
            for account in self.accounts:
                print(f"\n{Fore.BLUE}Processing: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                balance = await self.get_balance(account['address'])
                print(f"  💰 Balance: {balance:.4f} rSOL")
                
                if balance < (max_amount * num_transfers + 0.01):
                    print(f"  {Fore.RED}⚠️  Insufficient balance - skipping{Style.RESET_ALL}")
                    continue
                
                for i in range(num_transfers):
                    print(f"  [{i+1}/{num_transfers}] Sending transfer...")
                    
                    result = await self.send_random_transfer(account, min_amount, max_amount)
                    
                    if result['success']:
                        print(f"  {Fore.GREEN}✅ Sent {result['amount']:.4f} rSOL{Style.RESET_ALL}")
                        print(f"  {Fore.GREEN}   TX: {result['tx_hash']}{Style.RESET_ALL}")
                    else:
                        print(f"  {Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")
                    
                    if i < num_transfers - 1:
                        delay = random.uniform(min_delay, max_delay)
                        print(f"  ⏳ Waiting {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def random_operations_menu(self):
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🎲 RANDOM OPERATIONS (ALL IN ONE){Style.RESET_ALL}")
        
        try:
            deployments_per_account = int(input(f"{Fore.YELLOW}Deployments per account: {Style.RESET_ALL}"))
            transfers_per_account = int(input(f"{Fore.YELLOW}Transfers per account: {Style.RESET_ALL}"))
            min_transfer = float(input(f"{Fore.YELLOW}Min transfer amount (rSOL): {Style.RESET_ALL}"))
            max_transfer = float(input(f"{Fore.YELLOW}Max transfer amount (rSOL): {Style.RESET_ALL}"))
            min_delay = float(input(f"{Fore.YELLOW}Min delay (seconds): {Style.RESET_ALL}"))
            max_delay = float(input(f"{Fore.YELLOW}Max delay (seconds): {Style.RESET_ALL}"))
            
            contract_list = list(CONTRACTS.keys())
            
            for account in self.accounts:
                print(f"\n{Fore.BLUE}🔥 Processing: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                balance = await self.get_balance(account['address'])
                print(f"  💰 Balance: {balance:.4f} rSOL")
                
                if balance < 0.01:
                    print(f"  {Fore.RED}⚠️  Low balance - skipping{Style.RESET_ALL}")
                    continue
                
                # Deployments
                print(f"  🚀 Starting {deployments_per_account} deployments...")
                for i in range(deployments_per_account):
                    contract_key = random.choice(contract_list)
                    print(f"    [{i+1}] Deploying {CONTRACTS[contract_key]['name']}...")
                    
                    result = await self.deploy_contract(account, contract_key)
                    
                    if result['success']:
                        print(f"    {Fore.GREEN}✅ Success{Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.RED}❌ Failed{Style.RESET_ALL}")
                    
                    if i < deployments_per_account - 1:
                        delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(delay)
                
                # Transfers
                print(f"  💸 Starting {transfers_per_account} transfers...")
                for i in range(transfers_per_account):
                    result = await self.send_random_transfer(account, min_transfer, max_transfer)
                    
                    if result['success']:
                        print(f"    [{i+1}] {Fore.GREEN}✅ Sent {result['amount']:.4f} rSOL{Style.RESET_ALL}")
                    else:
                        print(f"    [{i+1}] {Fore.RED}❌ Failed{Style.RESET_ALL}")
                    
                    if i < transfers_per_account - 1:
                        delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(delay)
                        
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    def view_statistics(self):
        self.clear_screen()
        self.print_banner()
        self.print_stats()
        
        print(f"\n{Fore.CYAN}📋 DEPLOYED CONTRACTS:{Style.RESET_ALL}")
        
        total_contracts = 0
        for address, contracts in self.deployed_contracts.items():
            if contracts:
                print(f"\n{Fore.WHITE}Account: {address[:8]}...{address[-6:]}{Style.RESET_ALL}")
                for i, contract in enumerate(contracts, 1):
                    print(f"  {i}. {contract['name']} - {contract['address'][:8]}...{contract['address'][-6:]}")
                    total_contracts += 1
        
        print(f"\n{Fore.CYAN}Total Deployed Contracts: {total_contracts}{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    def settings_menu(self):
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🔧 SETTINGS{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Reload Accounts")
        print(f"2. Reload Proxies")
        print(f"3. Test Connection")
        print(f"4. Check Balances")
        print(f"5. Back to Main Menu{Style.RESET_ALL}")
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select option (1-5): {Style.RESET_ALL}")
            
            if choice == '1':
                self.accounts = []
                self.load_accounts()
                print(f"{Fore.GREEN}Accounts reloaded!{Style.RESET_ALL}")
            
            elif choice == '2':
                self.proxy_manager.load_proxies()
                if self.proxy_manager.proxies:
                    self.current_proxy = self.proxy_manager.get_random_proxy()
                    self.session.proxies = self.current_proxy
                print(f"{Fore.GREEN}Proxies reloaded!{Style.RESET_ALL}")
            
            elif choice == '3':
                asyncio.run(self.test_connection())
            
            elif choice == '4':
                asyncio.run(self.check_all_balances())
            
            elif choice == '5':
                return
            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def test_connection(self):
        try:
            connected = self.w3.is_connected()
            print(f"\n{Fore.CYAN}🌐 CONNECTION TEST{Style.RESET_ALL}")
            print(f"Status: {'🟢 CONNECTED' if connected else '🔴 DISCONNECTED'}")
            
            if connected:
                latest_block = self.w3.eth.block_number
                gas_price = self.w3.from_wei(self.w3.eth.gas_price, 'gwei')
                print(f"Latest Block: {latest_block}")
                print(f"Gas Price: {gas_price:.2f} Gwei")
                
                if self.current_proxy:
                    print(f"Proxy: {self.current_proxy['http'].split('@')[-1] if '@' in self.current_proxy['http'] else self.current_proxy['http'].split('/')[-1]}")
                else:
                    print("Proxy: Not used")
            
        except Exception as e:
            print(f"Error: {e}")
    
    async def check_all_balances(self):
        print(f"\n{Fore.CYAN}💰 ACCOUNT BALANCES{Style.RESET_ALL}")
        
        total_balance = 0
        for account in self.accounts:
            balance = await self.get_balance(account['address'])
            total_balance += balance
            print(f"{Fore.WHITE}{account['address'][:8]}...{account['address'][-6:]}: {balance:.4f} rSOL{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Total Balance: {total_balance:.4f} rSOL{Style.RESET_ALL}")
    
    async def interact_contracts_menu(self):
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🔗 CONTRACT INTERACTIONS{Style.RESET_ALL}")
        
        total_contracts = sum(len(contracts) for contracts in self.deployed_contracts.values())
        
        if total_contracts == 0:
            print(f"{Fore.RED}No contracts deployed yet! Deploy some contracts first.{Style.RESET_ALL}")
            input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}Found {total_contracts} deployed contracts{Style.RESET_ALL}")
        
        try:
            interactions_per_contract = int(input(f"{Fore.YELLOW}Interactions per contract: {Style.RESET_ALL}"))
            min_delay = float(input(f"{Fore.YELLOW}Min delay (seconds): {Style.RESET_ALL}"))
            max_delay = float(input(f"{Fore.YELLOW}Max delay (seconds): {Style.RESET_ALL}"))
            
            for account in self.accounts:
                if account['address'] not in self.deployed_contracts:
                    continue
                
                contracts = self.deployed_contracts[account['address']]
                if not contracts:
                    continue
                
                print(f"\n{Fore.BLUE}Interacting with contracts for: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                
                for contract in contracts:
                    print(f"  📋 Contract: {contract['name']}")
                    
                    for i in range(interactions_per_contract):
                        print(f"    [{i+1}] Sending interaction...")
                        
                        try:
                            # Build interaction transaction
                            transaction = self.build_transaction_params(
                                account,
                                to=contract['address'],
                                value=0,
                                gas=100000,
                                data='0x6057361d' + hex(random.randint(1, 1000000))[2:].zfill(64)  # store function
                            )
                            
                            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
                            
                            # Send with retry
                            for attempt in range(3):
                                try:
                                    raw_tx = getattr(signed_txn, 'raw_transaction', 
                                                   getattr(signed_txn, 'rawTransaction', None))
                                    
                                    if raw_tx is None:
                                        raise Exception("Could not get raw transaction")
                                    
                                    tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                                    break
                                except Exception as e:
                                    if attempt < 2:
                                        self.rotate_proxy()
                                        await asyncio.sleep(1)
                                        continue
                                    raise e
                            
                            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                            
                            self.stats['total_interactions'] += 1
                            
                            if receipt.status == 1:
                                self.stats['successful_interactions'] += 1
                                print(f"    {Fore.GREEN}✅ Success: {tx_hash.hex()}{Style.RESET_ALL}")
                            else:
                                print(f"    {Fore.RED}❌ Transaction failed{Style.RESET_ALL}")
                                
                        except Exception as e:
                            self.stats['total_interactions'] += 1
                            print(f"    {Fore.RED}❌ Error: {str(e)[:50]}{Style.RESET_ALL}")
                        
                        if i < interactions_per_contract - 1:
                            delay = random.uniform(min_delay, max_delay)
                            await asyncio.sleep(delay)
                            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def run(self):
        # Test connection first
        try:
            if not self.w3.is_connected():
                print(f"{Fore.RED}❌ Cannot connect to Martius network!{Style.RESET_ALL}")
                return
        except Exception as e:
            print(f"{Fore.RED}❌ Connection error: {e}{Style.RESET_ALL}")
            return
        
        if len(self.accounts) == 0:
            print(f"{Fore.RED}❌ No accounts found! Add private keys to accounts.txt{Style.RESET_ALL}")
            return
        
        while True:
            self.clear_screen()
            self.print_banner()
            self.print_stats()
            self.print_menu()
            
            try:
                choice = input(f"\n{Fore.YELLOW}Enter your choice (1-7): {Style.RESET_ALL}")
                
                if choice == '1':
                    await self.deploy_contracts_menu()
                
                elif choice == '2':
                    await self.interact_contracts_menu()
                
                elif choice == '3':
                    await self.send_transfers_menu()
                
                elif choice == '4':
                    self.view_statistics()
                
                elif choice == '5':
                    await self.random_operations_menu()
                
                elif choice == '6':
                    self.settings_menu()
                
                elif choice == '7':
                    self.clear_screen()
                    print(f"{Fore.CYAN}Thanks for using Martius Bot! 🚀{Style.RESET_ALL}")
                    break
                
                else:
                    print(f"{Fore.RED}Invalid choice!{Style.RESET_ALL}")
                    input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
            
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
                input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
                input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")

async def main():
    try:
        if not os.path.exists("contracts.py"):
            print(f"{Fore.RED}❌ contracts.py file not found!{Style.RESET_ALL}")
            return
        
        bot = MartianBot()
        await bot.run()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    # Check required packages
    try:
        import colorama
        from web3 import Web3
        from eth_account import Account
    except ImportError as e:
        print(f"Missing package: {e}")
        print("Install with: pip install web3 colorama eth-account requests")
        sys.exit(1)
    
    asyncio.run(main())
