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
    print(f"{Fore.RED}❌ contracts.py file not found! Please ensure contracts.py is in the same directory.{Style.RESET_ALL}")
    sys.exit(1)

# Network Configuration
NETWORK_CONFIG = {
    "name": "Martius",
    "chain_id": 121214,
    "rpc_url": "https://martius-i.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

class MartianBot:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(NETWORK_CONFIG["rpc_url"]))
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
        
        # Create required files
        self.create_files_if_not_exist()
        self.load_accounts()
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def create_files_if_not_exist(self):
        """Create required files if they don't exist"""
        if not os.path.exists("accounts.txt"):
            with open("accounts.txt", "w") as f:
                f.write("# Add your private keys here (one per line)\n")
                f.write("# Example: 0x1234567890abcdef...\n")
            print(f"{Fore.YELLOW}✓ Created accounts.txt - Please add your private keys{Style.RESET_ALL}")
        
        if not os.path.exists("deployed_contracts.json"):
            with open("deployed_contracts.json", "w") as f:
                json.dump({}, f)
        
        # Load deployed contracts
        try:
            with open("deployed_contracts.json", "r") as f:
                self.deployed_contracts = json.load(f)
        except:
            self.deployed_contracts = {}
    
    def save_deployed_contracts(self):
        """Save deployed contracts to file"""
        try:
            with open("deployed_contracts.json", "w") as f:
                json.dump(self.deployed_contracts, f, indent=2)
        except Exception as e:
            print(f"{Fore.RED}Error saving contracts: {e}{Style.RESET_ALL}")
    
    def load_accounts(self):
        """Load accounts from accounts.txt"""
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
                except Exception as e:
                    print(f"{Fore.RED}Invalid private key: {line[:10]}...{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}✓ Loaded {len(self.accounts)} accounts{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading accounts: {e}{Style.RESET_ALL}")
    
    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    🚀 MARTIUS NETWORK BOT 🚀                  ║
║                       Simple & Fast Bot                       ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}Network: {NETWORK_CONFIG['name']} | Chain ID: {NETWORK_CONFIG['chain_id']}
Currency: {NETWORK_CONFIG['currency']}
Accounts: {len(self.accounts)} | Contracts Available: {len(CONTRACTS)}{Style.RESET_ALL}
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
        """Get account balance"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except:
            return 0.0
    
    async def deploy_contract(self, account: Dict, contract_key: str) -> Dict:
        """Deploy a simple contract using direct bytecode"""
        try:
            contract_info = CONTRACTS[contract_key]
            print(f"    📋 Contract: {contract_key}")
            print(f"    🔧 Preparing deployment...")
            
            # Simplified deployment - just send a contract creation transaction
            nonce = self.w3.eth.get_transaction_count(account['address'])
            
            # Simple contract bytecode (a basic storage contract)
            # This is a minimal working contract that just stores a value
            simple_bytecode = "0x608060405234801561001057600080fd5b5060c78061001f6000396000f3fe6080604052348015600f57600080fd5b506004361060325760003560e01c80632e64cec11460375780636057361d146051575b600080fd5b60005460405190815260200160405180910390f35b605f605c3660046059565b600055565b005b600060208284031215606a57600080fd5b503591905056fea26469706673582212208bb471f2c5b70068a15ee31e3d21c7b0659a56d888b5b07b9c46aee2bcf0db0764736f6c63430008130033"
            
            transaction = {
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'data': simple_bytecode,
                'chainId': NETWORK_CONFIG["chain_id"]
            }
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            print(f"    ⏳ Waiting for confirmation...")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                contract_address = receipt.contractAddress
                
                # Save deployment info
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
                
                self.stats['total_deployments'] += 1
                self.stats['successful_deployments'] += 1
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'contract_address': contract_address,
                    'gas_used': receipt.gasUsed
                }
            else:
                self.stats['total_deployments'] += 1
                return {'success': False, 'error': 'Transaction failed'}
                
        except Exception as e:
            self.stats['total_deployments'] += 1
            return {'success': False, 'error': str(e)}
    
    async def send_random_transfer(self, account: Dict, min_amount: float, max_amount: float) -> Dict:
        """Send random transfer to random address"""
        try:
            # Generate random recipient
            random_recipient = '0x' + ''.join(random.choices('0123456789abcdef', k=40))
            
            # Random amount between min and max
            amount = random.uniform(min_amount, max_amount)
            amount_wei = self.w3.to_wei(amount, 'ether')
            
            # Check balance
            balance = await self.get_balance(account['address'])
            if balance < (amount + 0.001):  # Keep some for gas
                return {'success': False, 'error': f'Insufficient balance: {balance:.4f} rSOL'}
            
            nonce = self.w3.eth.get_transaction_count(account['address'])
            
            transaction = {
                'to': random_recipient,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
                'chainId': NETWORK_CONFIG["chain_id"]
            }
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
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
        """Deploy contracts menu"""
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
                # Random deployment
                num_deployments = int(input(f"{Fore.YELLOW}Number of deployments per account: {Style.RESET_ALL}"))
                min_delay = float(input(f"{Fore.YELLOW}Minimum delay (seconds): {Style.RESET_ALL}"))
                max_delay = float(input(f"{Fore.YELLOW}Maximum delay (seconds): {Style.RESET_ALL}"))
                
                for account in self.accounts:
                    print(f"\n{Fore.BLUE}Processing: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                    balance = await self.get_balance(account['address'])
                    print(f"  💰 Balance: {balance:.4f} rSOL")
                    
                    if balance < 0.01:
                        print(f"  {Fore.RED}⚠️ Low balance - skipping{Style.RESET_ALL}")
                        continue
                    
                    for i in range(num_deployments):
                        contract_key = random.choice(contract_list)
                        print(f"  [{i+1}/{num_deployments}] Deploying {CONTRACTS[contract_key]['name']}...")
                        
                        result = await self.deploy_contract(account, contract_key)
                        
                        if result['success']:
                            print(f"  {Fore.GREEN}✅ Success: {result['contract_address']}{Style.RESET_ALL}")
                            print(f"  {Fore.GREEN}   TX: {result['tx_hash']}{Style.RESET_ALL}")
                            print(f"  {Fore.GREEN}   Gas: {result['gas_used']:,}{Style.RESET_ALL}")
                        else:
                            print(f"  {Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")
                        
                        if i < num_deployments - 1:
                            delay = random.uniform(min_delay, max_delay)
                            print(f"  ⏳ Waiting {delay:.1f}s...")
                            await asyncio.sleep(delay)
            
            else:
                # Specific contract
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
        """Send random transfers menu"""
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}💸 RANDOM TRANSFERS{Style.RESET_ALL}")
        
        try:
            min_amount = float(input(f"{Fore.YELLOW}Minimum transfer amount (rSOL): {Style.RESET_ALL}"))
            max_amount = float(input(f"{Fore.YELLOW}Maximum transfer amount (rSOL): {Style.RESET_ALL}"))
            num_transfers = int(input(f"{Fore.YELLOW}Number of transfers per account: {Style.RESET_ALL}"))
            min_delay = float(input(f"{Fore.YELLOW}Minimum delay (seconds): {Style.RESET_ALL}"))
            max_delay = float(input(f"{Fore.YELLOW}Maximum delay (seconds): {Style.RESET_ALL}"))
            
            for account in self.accounts:
                print(f"\n{Fore.BLUE}Processing: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                balance = await self.get_balance(account['address'])
                print(f"  💰 Balance: {balance:.4f} rSOL")
                
                if balance < (max_amount * num_transfers + 0.01):
                    print(f"  {Fore.RED}⚠️ Insufficient balance - skipping{Style.RESET_ALL}")
                    continue
                
                for i in range(num_transfers):
                    print(f"  [{i+1}/{num_transfers}] Sending transfer...")
                    
                    result = await self.send_random_transfer(account, min_amount, max_amount)
                    
                    if result['success']:
                        print(f"  {Fore.GREEN}✅ Sent {result['amount']:.4f} rSOL to {result['recipient'][:8]}...{result['recipient'][-6:]}{Style.RESET_ALL}")
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
        """All-in-one random operations"""
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
                    print(f"  {Fore.RED}⚠️ Low balance - skipping{Style.RESET_ALL}")
                    continue
                
                # Random deployments
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
                
                # Random transfers
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
        """View detailed statistics"""
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
        """Settings menu"""
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🔧 SETTINGS{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Reload Accounts")
        print(f"2. Clear Deployed Contracts History")
        print(f"3. Network Information")
        print(f"4. Check Balances")
        print(f"5. Back to Main Menu{Style.RESET_ALL}")
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select option (1-5): {Style.RESET_ALL}")
            
            if choice == '1':
                self.accounts = []
                self.load_accounts()
                print(f"{Fore.GREEN}Accounts reloaded!{Style.RESET_ALL}")
            
            elif choice == '2':
                self.deployed_contracts = {}
                self.save_deployed_contracts()
                print(f"{Fore.GREEN}Deployed contracts history cleared!{Style.RESET_ALL}")
            
            elif choice == '3':
                self.show_network_info()
            
            elif choice == '4':
                asyncio.run(self.check_all_balances())
            
            elif choice == '5':
                return
            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    def show_network_info(self):
        """Show network information"""
        connected = self.w3.is_connected()
        
        print(f"\n{Fore.CYAN}🌐 NETWORK INFORMATION{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Network: {NETWORK_CONFIG['name']}")
        print(f"Chain ID: {NETWORK_CONFIG['chain_id']}")
        print(f"RPC URL: {NETWORK_CONFIG['rpc_url']}")
        print(f"Currency: {NETWORK_CONFIG['currency']}")
        print(f"Connection: {'🟢 CONNECTED' if connected else '🔴 DISCONNECTED'}{Style.RESET_ALL}")
        
        if connected:
            try:
                latest_block = self.w3.eth.block_number
                gas_price = self.w3.from_wei(self.w3.eth.gas_price, 'gwei')
                print(f"{Fore.WHITE}Latest Block: {latest_block}")
                print(f"Gas Price: {gas_price:.2f} Gwei{Style.RESET_ALL}")
            except:
                pass
    
    async def check_all_balances(self):
        """Check all account balances"""
        print(f"\n{Fore.CYAN}💰 ACCOUNT BALANCES{Style.RESET_ALL}")
        
        total_balance = 0
        for account in self.accounts:
            balance = await self.get_balance(account['address'])
            total_balance += balance
            print(f"{Fore.WHITE}{account['address'][:8]}...{account['address'][-6:]}: {balance:.4f} rSOL{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Total Balance: {total_balance:.4f} rSOL{Style.RESET_ALL}")
    
    async def interact_contracts_menu(self):
        """Interact with deployed contracts"""
        self.clear_screen()
        self.print_banner()
        
        print(f"\n{Fore.CYAN}🔗 CONTRACT INTERACTIONS{Style.RESET_ALL}")
        
        # Count deployed contracts
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
                    
                    # Simple interaction - just send a transaction to the contract
                    for i in range(interactions_per_contract):
                        print(f"    [{i+1}] Sending interaction...")
                        
                        try:
                            nonce = self.w3.eth.get_transaction_count(account['address'])
                            
                            # Simple call to contract (store function with random value)
                            transaction = {
                                'to': contract['address'],
                                'value': 0,
                                'gas': 100000,
                                'gasPrice': self.w3.eth.gas_price,
                                'nonce': nonce,
                                'data': '0x6057361d' + hex(random.randint(1, 1000000))[2:].zfill(64),  # store(uint256)
                                'chainId': NETWORK_CONFIG["chain_id"]
                            }
                            
                            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
                            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                            
                            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                            
                            self.stats['total_interactions'] += 1
                            
                            if receipt.status == 1:
                                self.stats['successful_interactions'] += 1
                                print(f"    {Fore.GREEN}✅ Success: {tx_hash.hex()}{Style.RESET_ALL}")
                            else:
                                print(f"    {Fore.RED}❌ Transaction failed{Style.RESET_ALL}")
                                
                        except Exception as e:
                            self.stats['total_interactions'] += 1
                            print(f"    {Fore.RED}❌ Error: {str(e)[:50]}...{Style.RESET_ALL}")
                        
                        if i < interactions_per_contract - 1:
                            delay = random.uniform(min_delay, max_delay)
                            await asyncio.sleep(delay)
                            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
        
        input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def run(self):
        """Main bot loop"""
        
        # Check connection
        if not self.w3.is_connected():
            print(f"{Fore.RED}❌ Cannot connect to Martius network!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please check your internet connection{Style.RESET_ALL}")
            return
        
        if len(self.accounts) == 0:
            print(f"{Fore.RED}❌ No accounts found!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please add private keys to accounts.txt{Style.RESET_ALL}")
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
    """Main function"""
    try:
        # Check if contracts.py exists
        if not os.path.exists("contracts.py"):
            print(f"{Fore.RED}❌ contracts.py file not found!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please ensure contracts.py is in the same directory.{Style.RESET_ALL}")
            return
        
        # Initialize bot
        bot = MartianBot()
        
        # Run bot
        await bot.run()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    # Install required packages
    try:
        import colorama
        from web3 import Web3
        from eth_account import Account
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Install with: pip install web3 colorama eth-account")
        sys.exit(1)
    
    asyncio.run(main())
