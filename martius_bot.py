#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from colorama import init, Fore, Back, Style
from tabulate import tabulate
from web3 import Web3
from eth_account import Account
import solcx
from contracts import CONTRACTS

# Initialize colorama
init(autoreset=True)

# Network Configuration
NETWORK_CONFIG = {
    "name": "Martius",
    "chain_id": 121214,
    "rpc_url": "https://martius-i.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

@dataclass
class TransactionResult:
    success: bool
    tx_hash: Optional[str]
    error: Optional[str]
    contract_address: Optional[str] = None
    gas_used: Optional[int] = None

@dataclass
class AccountStats:
    address: str
    balance: float
    deployed_contracts: int
    successful_interactions: int
    failed_transactions: int
    total_gas_used: int

class ProxyManager:
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.load_proxies()
    
    def load_proxies(self):
        try:
            if not os.path.exists(self.proxy_file):
                return
            
            with open(self.proxy_file, 'r') as f:
                lines = f.read().strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                proxy = self.parse_proxy(line.strip())
                if proxy:
                    self.proxies.append(proxy)
            
            print(f"{Fore.GREEN}✓ Loaded {len(self.proxies)} proxies")
        except Exception as e:
            print(f"{Fore.RED}✗ Error loading proxies: {e}")
    
    def parse_proxy(self, line: str) -> Optional[Dict]:
        try:
            # Format: ip:port or ip:port:user:pass or user:pass@ip:port
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
        self.w3 = Web3(Web3.HTTPProvider(NETWORK_CONFIG["rpc_url"]))
        self.accounts = []
        self.proxy_manager = ProxyManager()
        self.stats = {}
        self.deployed_contracts = {}
        self.use_proxy = False
        
        # Install solidity compiler
        try:
            solcx.install_solc('0.8.19')
            solcx.set_solc_version('0.8.19')
        except:
            pass
        
        self.load_accounts()
    
    def load_accounts(self):
        try:
            if not os.path.exists("accounts.txt"):
                print(f"{Fore.RED}✗ accounts.txt file not found!")
                return
            
            with open("accounts.txt", 'r') as f:
                lines = f.read().strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                private_key = line.strip()
                if not private_key.startswith('0x'):
                    private_key = '0x' + private_key
                
                try:
                    account = Account.from_key(private_key)
                    self.accounts.append({
                        'private_key': private_key,
                        'address': account.address,
                        'account': account
                    })
                    
                    self.stats[account.address] = AccountStats(
                        address=account.address,
                        balance=0.0,
                        deployed_contracts=0,
                        successful_interactions=0,
                        failed_transactions=0,
                        total_gas_used=0
                    )
                except Exception as e:
                    print(f"{Fore.RED}✗ Invalid private key: {line[:10]}...")
            
            print(f"{Fore.GREEN}✓ Loaded {len(self.accounts)} accounts")
        except Exception as e:
            print(f"{Fore.RED}✗ Error loading accounts: {e}")
    
    async def get_balance(self, address: str) -> float:
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_eth)
        except:
            return 0.0
    
    def compile_contract(self, contract_code: str) -> Dict:
        try:
            compiled = solcx.compile_source(contract_code)
            contract_id, contract_interface = compiled.popitem()
            return contract_interface
        except Exception as e:
            print(f"{Fore.RED}✗ Compilation error: {e}")
            return {}
    
    async def deploy_contract(self, account: Dict, contract_name: str, use_proxy: bool = False) -> TransactionResult:
        try:
            contract_info = CONTRACTS[contract_name]
            compiled_contract = self.compile_contract(contract_info["code"])
            
            if not compiled_contract:
                return TransactionResult(False, None, "Compilation failed")
            
            # Get contract bytecode and ABI
            bytecode = compiled_contract['bytecode']
            abi = compiled_contract['abi']
            
            # Create contract instance
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Get nonce
            nonce = self.w3.eth.get_transaction_count(account['address'])
            
            # Estimate gas
            try:
                gas_estimate = contract.constructor().estimate_gas({
                    'from': account['address']
                })
                gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
            except:
                gas_limit = 2000000  # Default gas limit
            
            # Get gas price
            gas_price = self.w3.eth.gas_price
            
            # Build transaction
            transaction = contract.constructor().build_transaction({
                'from': account['address'],
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': NETWORK_CONFIG["chain_id"]
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                # Store deployed contract info
                contract_address = receipt.contractAddress
                if account['address'] not in self.deployed_contracts:
                    self.deployed_contracts[account['address']] = []
                
                self.deployed_contracts[account['address']].append({
                    'name': contract_name,
                    'address': contract_address,
                    'abi': abi,
                    'tx_hash': tx_hash.hex()
                })
                
                # Update stats
                self.stats[account['address']].deployed_contracts += 1
                self.stats[account['address']].total_gas_used += receipt.gasUsed
                
                return TransactionResult(
                    True, 
                    tx_hash.hex(), 
                    None, 
                    contract_address,
                    receipt.gasUsed
                )
            else:
                return TransactionResult(False, tx_hash.hex(), "Transaction failed")
                
        except Exception as e:
            return TransactionResult(False, None, str(e))
    
    async def interact_with_contract(self, account: Dict, contract_info: Dict, interaction_type: str) -> TransactionResult:
        try:
            contract = self.w3.eth.contract(
                address=contract_info['address'],
                abi=contract_info['abi']
            )
            
            nonce = self.w3.eth.get_transaction_count(account['address'])
            gas_price = self.w3.eth.gas_price
            
            # Prepare interaction based on contract type and function
            transaction = None
            
            if contract_info['name'] == 'voting' and interaction_type == 'vote':
                # Vote on proposal 0 with random choice
                vote_choice = random.choice([True, False])
                transaction = contract.functions.vote(0, vote_choice).build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            elif contract_info['name'] == 'voting' and interaction_type == 'createProposal':
                proposal_text = f"Proposal {random.randint(1, 1000)}"
                transaction = contract.functions.createProposal(proposal_text).build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            elif contract_info['name'] == 'token' and interaction_type == 'transfer':
                # Transfer small amount to random address
                random_recipient = '0x' + ''.join(random.choices('0123456789abcdef', k=40))
                amount = self.w3.to_wei(0.001, 'ether')
                transaction = contract.functions.transfer(random_recipient, amount).build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            elif contract_info['name'] == 'nft' and interaction_type == 'mint':
                transaction = contract.functions.mint(account['address']).build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            elif contract_info['name'] == 'lottery' and interaction_type == 'enterLottery':
                transaction = contract.functions.enterLottery().build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'value': self.w3.to_wei(0.01, 'ether'),
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            elif contract_info['name'] == 'staking' and interaction_type == 'stake':
                transaction = contract.functions.stake().build_transaction({
                    'from': account['address'],
                    'gas': 200000,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'value': self.w3.to_wei(0.01, 'ether'),
                    'chainId': NETWORK_CONFIG["chain_id"]
                })
            
            # Add more interactions for other contracts...
            
            if not transaction:
                return TransactionResult(False, None, f"Interaction {interaction_type} not implemented")
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                self.stats[account['address']].successful_interactions += 1
                self.stats[account['address']].total_gas_used += receipt.gasUsed
                return TransactionResult(True, tx_hash.hex(), None, None, receipt.gasUsed)
            else:
                self.stats[account['address']].failed_transactions += 1
                return TransactionResult(False, tx_hash.hex(), "Transaction failed")
        
        except Exception as e:
            self.stats[account['address']].failed_transactions += 1
            return TransactionResult(False, None, str(e))
    
    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    🚀 MARTIUS NETWORK BOT 🚀                  ║
║                  Smart Contract Deployment Tool               ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}Network: {NETWORK_CONFIG['name']} | Chain ID: {NETWORK_CONFIG['chain_id']}
RPC: {NETWORK_CONFIG['rpc_url']}
Currency: {NETWORK_CONFIG['currency']}
Explorer: {NETWORK_CONFIG['explorer']}{Style.RESET_ALL}

{Fore.GREEN}✓ Accounts Loaded: {len(self.accounts)}
✓ Available Contracts: {len(CONTRACTS)}
✓ Proxies Available: {len(self.proxy_manager.proxies)}{Style.RESET_ALL}
        """
        print(banner)
    
    def print_menu(self):
        menu = f"""
{Fore.CYAN}╔═══════════════ MAIN MENU ═══════════════╗{Style.RESET_ALL}
{Fore.WHITE}║  1. Deploy Contracts                    ║
║  2. Interact with Contracts             ║
║  3. Check Account Balances              ║
║  4. View Transaction History            ║
║  5. Random Operations                   ║
║  6. Settings                            ║
║  7. Exit                                ║{Style.RESET_ALL}
{Fore.CYAN}╚═════════════════════════════════════════╝{Style.RESET_ALL}
        """
        print(menu)
    
    def print_contracts_menu(self):
        print(f"\n{Fore.CYAN}Available Contracts:{Style.RESET_ALL}")
        for i, (key, contract) in enumerate(CONTRACTS.items(), 1):
            print(f"{Fore.WHITE}{i:2d}. {contract['name']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{len(CONTRACTS)+1:2d}. Random Selection{Style.RESET_ALL}")
    
    async def update_balances(self):
        for account in self.accounts:
            balance = await self.get_balance(account['address'])
            self.stats[account['address']].balance = balance
    
    def print_account_stats(self):
        print(f"\n{Fore.CYAN}📊 ACCOUNT STATISTICS{Style.RESET_ALL}")
        
        headers = ["Address", "Balance (rSOL)", "Contracts", "Interactions", "Failed TX", "Gas Used"]
        table_data = []
        
        for account in self.accounts:
            stats = self.stats[account['address']]
            table_data.append([
                f"{stats.address[:8]}...{stats.address[-6:]}",
                f"{stats.balance:.4f}",
                stats.deployed_contracts,
                stats.successful_interactions,
                stats.failed_transactions,
                f"{stats.total_gas_used:,}"
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    async def deploy_contracts_menu(self):
        print(f"\n{Fore.CYAN}🚀 CONTRACT DEPLOYMENT{Style.RESET_ALL}")
        
        self.print_contracts_menu()
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select contract type (1-{len(CONTRACTS)+1}): {Style.RESET_ALL}")
            
            if choice == str(len(CONTRACTS)+1):
                # Random selection
                num_deployments = int(input(f"{Fore.YELLOW}Number of deployments per account: {Style.RESET_ALL}"))
                min_delay = float(input(f"{Fore.YELLOW}Minimum delay between transactions (seconds): {Style.RESET_ALL}"))
                max_delay = float(input(f"{Fore.YELLOW}Maximum delay between transactions (seconds): {Style.RESET_ALL}"))
                
                use_proxy = input(f"{Fore.YELLOW}Use proxy? (y/n): {Style.RESET_ALL}").lower() == 'y'
                
                for account in self.accounts:
                    print(f"\n{Fore.BLUE}Processing account: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                    
                    for i in range(num_deployments):
                        # Random contract selection
                        contract_key = random.choice(list(CONTRACTS.keys()))
                        contract_name = CONTRACTS[contract_key]['name']
                        
                        print(f"  {Fore.YELLOW}Deploying {contract_name}...{Style.RESET_ALL}")
                        
                        result = await self.deploy_contract(account, contract_key, use_proxy)
                        
                        if result.success:
                            print(f"  {Fore.GREEN}✓ Deployed: {result.contract_address}{Style.RESET_ALL}")
                            print(f"  {Fore.GREEN}  TX: {result.tx_hash}{Style.RESET_ALL}")
                            print(f"  {Fore.GREEN}  Gas: {result.gas_used:,}{Style.RESET_ALL}")
                        else:
                            print(f"  {Fore.RED}✗ Failed: {result.error}{Style.RESET_ALL}")
                        
                        # Random delay
                        if i < num_deployments - 1:
                            delay = random.uniform(min_delay, max_delay)
                            print(f"  {Fore.BLUE}⏳ Waiting {delay:.2f}s...{Style.RESET_ALL}")
                            await asyncio.sleep(delay)
            else:
                # Specific contract selection
                contract_index = int(choice) - 1
                contract_keys = list(CONTRACTS.keys())
                
                if 0 <= contract_index < len(contract_keys):
                    contract_key = contract_keys[contract_index]
                    use_proxy = input(f"{Fore.YELLOW}Use proxy? (y/n): {Style.RESET_ALL}").lower() == 'y'
                    
                    for account in self.accounts:
                        print(f"\n{Fore.BLUE}Deploying for account: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
                        
                        result = await self.deploy_contract(account, contract_key, use_proxy)
                        
                        if result.success:
                            print(f"{Fore.GREEN}✓ Deployed: {result.contract_address}{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}  TX: {result.tx_hash}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}✗ Failed: {result.error}{Style.RESET_ALL}")
        
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
    
    async def interact_with_contracts_menu(self):
        print(f"\n{Fore.CYAN}🔗 CONTRACT INTERACTIONS{Style.RESET_ALL}")
        
        # Show deployed contracts
        total_contracts = 0
        for address, contracts in self.deployed_contracts.items():
            total_contracts += len(contracts)
        
        if total_contracts == 0:
            print(f"{Fore.RED}No contracts deployed yet!{Style.RESET_ALL}")
            return
        
        num_interactions = int(input(f"{Fore.YELLOW}Number of interactions per contract: {Style.RESET_ALL}"))
        min_delay = float(input(f"{Fore.YELLOW}Minimum delay between interactions (seconds): {Style.RESET_ALL}"))
        max_delay = float(input(f"{Fore.YELLOW}Maximum delay between interactions (seconds): {Style.RESET_ALL}"))
        
        use_proxy = input(f"{Fore.YELLOW}Use proxy? (y/n): {Style.RESET_ALL}").lower() == 'y'
        
        for account in self.accounts:
            if account['address'] not in self.deployed_contracts:
                continue
            
            print(f"\n{Fore.BLUE}Interacting with contracts for: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
            
            for contract_info in self.deployed_contracts[account['address']]:
                contract_name = contract_info['name']
                available_interactions = CONTRACTS[contract_name]['interactions']
                
                print(f"  {Fore.YELLOW}Contract: {CONTRACTS[contract_name]['name']} at {contract_info['address'][:8]}...{contract_info['address'][-6:]}{Style.RESET_ALL}")
                
                for i in range(num_interactions):
                    interaction = random.choice(available_interactions)
                    print(f"    {Fore.CYAN}Calling {interaction}...{Style.RESET_ALL}")
                    
                    result = await self.interact_with_contract(account, contract_info, interaction)
                    
                    if result.success:
                        print(f"    {Fore.GREEN}✓ Success: {result.tx_hash}{Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.RED}✗ Failed: {result.error}{Style.RESET_ALL}")
                    
                    if i < num_interactions - 1:
                        delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(delay)
    
    async def run(self):
        self.print_banner()
        
        while True:
            self.print_menu()
            
            try:
                choice = input(f"\n{Fore.YELLOW}Enter your choice (1-7): {Style.RESET_ALL}")
                
                if choice == '1':
                    await self.deploy_contracts_menu()
                
                elif choice == '2':
                    await self.interact_with_contracts_menu()
                
                elif choice == '3':
                    print(f"\n{Fore.CYAN}💰 Updating balances...{Style.RESET_ALL}")
                    await self.update_balances()
                    self.print_account_stats()
                
                elif choice == '4':
                    self.print_account_stats()
                
                elif choice == '5':
                    await self.random_operations_menu()
                
                elif choice == '6':
                    self.settings_menu()
                
                elif choice == '7':
                    print(f"{Fore.CYAN}👋 Thanks for using Martius Bot!{Style.RESET_ALL}")
                    break
                
                else:
                    print(f"{Fore.RED}Invalid choice!{Style.RESET_ALL}")
            
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            
            input(f"\n{Fore.BLUE}Press Enter to continue...{Style.RESET_ALL}")
    
    async def random_operations_menu(self):
        print(f"\n{Fore.CYAN}🎲 RANDOM OPERATIONS{Style.RESET_ALL}")
        
        num_deployments = int(input(f"{Fore.YELLOW}Number of random deployments per account: {Style.RESET_ALL}"))
        num_interactions = int(input(f"{Fore.YELLOW}Number of random interactions per deployed contract: {Style.RESET_ALL}"))
        min_delay = float(input(f"{Fore.YELLOW}Minimum delay between transactions (seconds): {Style.RESET_ALL}"))
        max_delay = float(input(f"{Fore.YELLOW}Maximum delay between transactions (seconds): {Style.RESET_ALL}"))
        
        use_proxy = input(f"{Fore.YELLOW}Use proxy? (y/n): {Style.RESET_ALL}").lower() == 'y'
        
        for account in self.accounts:
            print(f"\n{Fore.BLUE}🔥 Processing account: {account['address'][:8]}...{account['address'][-6:]}{Style.RESET_ALL}")
            
            # Random deployments
            for i in range(num_deployments):
                contract_key = random.choice(list(CONTRACTS.keys()))
                contract_name = CONTRACTS[contract_key]['name']
                
                print(f"  {Fore.YELLOW}[{i+1}/{num_deployments}] Deploying {contract_name}...{Style.RESET_ALL}")
                
                result = await self.deploy_contract(account, contract_key, use_proxy)
                
                if result.success:
                    print(f"  {Fore.GREEN}✓ Deployed at: {result.contract_address}{Style.RESET_ALL}")
                    print(f"  {Fore.GREEN}  TX Hash: {result.tx_hash}{Style.RESET_ALL}")
                    print(f"  {Fore.GREEN}  Gas Used: {result.gas_used:,}{Style.RESET_ALL}")
                else:
                    print(f"  {Fore.RED}✗ Deployment failed: {result.error}{Style.RESET_ALL}")
                
                # Random delay
                if i < num_deployments - 1:
                    delay = random.uniform(min_delay, max_delay)
                    print(f"  {Fore.BLUE}⏳ Waiting {delay:.2f}s...{Style.RESET_ALL}")
                    await asyncio.sleep(delay)
            
            # Random interactions with deployed contracts
            if account['address'] in self.deployed_contracts:
                print(f"  {Fore.CYAN}🔗 Starting interactions...{Style.RESET_ALL}")
                
                for contract_info in self.deployed_contracts[account['address']]:
                    contract_name = contract_info['name']
                    available_interactions = CONTRACTS[contract_name]['interactions']
                    
                    print(f"    {Fore.MAGENTA}Contract: {CONTRACTS[contract_name]['name']}{Style.RESET_ALL}")
                    
                    for j in range(num_interactions):
                        interaction = random.choice(available_interactions)
                        print(f"      {Fore.CYAN}[{j+1}/{num_interactions}] Calling {interaction}...{Style.RESET_ALL}")
                        
                        result = await self.interact_with_contract(account, contract_info, interaction)
                        
                        if result.success:
                            print(f"      {Fore.GREEN}✓ Success: {result.tx_hash}{Style.RESET_ALL}")
                            print(f"      {Fore.GREEN}  Gas Used: {result.gas_used:,}{Style.RESET_ALL}")
                        else:
                            print(f"      {Fore.RED}✗ Failed: {result.error}{Style.RESET_ALL}")
                        
                        # Random delay
                        if j < num_interactions - 1:
                            delay = random.uniform(min_delay, max_delay)
                            await asyncio.sleep(delay)
    
    def settings_menu(self):
        settings_menu = f"""
{Fore.CYAN}⚙️  SETTINGS MENU{Style.RESET_ALL}
{Fore.WHITE}1. Toggle Proxy Usage
2. Reload Accounts
3. Reload Proxies
4. Network Information
5. Back to Main Menu{Style.RESET_ALL}
        """
        print(settings_menu)
        
        try:
            choice = input(f"\n{Fore.YELLOW}Select option (1-5): {Style.RESET_ALL}")
            
            if choice == '1':
                self.use_proxy = not self.use_proxy
                status = "ENABLED" if self.use_proxy else "DISABLED"
                print(f"{Fore.GREEN}Proxy usage: {status}{Style.RESET_ALL}")
            
            elif choice == '2':
                self.accounts = []
                self.stats = {}
                self.load_accounts()
                print(f"{Fore.GREEN}Accounts reloaded successfully!{Style.RESET_ALL}")
            
            elif choice == '3':
                self.proxy_manager.load_proxies()
                print(f"{Fore.GREEN}Proxies reloaded successfully!{Style.RESET_ALL}")
            
            elif choice == '4':
                self.print_network_info()
            
            elif choice == '5':
                return
            
        except ValueError:
            print(f"{Fore.RED}Invalid input!{Style.RESET_ALL}")
    
    def print_network_info(self):
        info = f"""
{Fore.CYAN}🌐 NETWORK INFORMATION{Style.RESET_ALL}
{Fore.WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Network Name: {NETWORK_CONFIG['name']}
Chain ID: {NETWORK_CONFIG['chain_id']}
RPC URL: {NETWORK_CONFIG['rpc_url']}
Currency Symbol: {NETWORK_CONFIG['currency']}
Block Explorer: {NETWORK_CONFIG['explorer']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Connection Status: {"🟢 CONNECTED" if self.w3.is_connected() else "🔴 DISCONNECTED"}
Latest Block: {self.w3.eth.block_number if self.w3.is_connected() else "N/A"}
Gas Price: {self.w3.from_wei(self.w3.eth.gas_price, 'gwei') if self.w3.is_connected() else "N/A"} Gwei{Style.RESET_ALL}
        """
        print(info)

async def main():
    try:
        # Check required files
        if not os.path.exists("accounts.txt"):
            print(f"{Fore.RED}❌ accounts.txt file is required!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Create accounts.txt with private keys (one per line){Style.RESET_ALL}")
            return
        
        # Initialize bot
        bot = MartianBot()
        
        if len(bot.accounts) == 0:
            print(f"{Fore.RED}❌ No valid accounts found in accounts.txt{Style.RESET_ALL}")
            return
        
        # Check connection
        if not bot.w3.is_connected():
            print(f"{Fore.RED}❌ Cannot connect to Martius network!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please check your internet connection and RPC URL{Style.RESET_ALL}")
            return
        
        # Run bot
        await bot.run()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
