#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import asyncio
from datetime import datetime
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
import requests
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Import contracts
try:
    from contracts import CONTRACTS
except ImportError:
    print(f"{Fore.RED}contracts.py file not found!{Style.RESET_ALL}")
    sys.exit(1)

# Network Configuration
NETWORK_CONFIG = {
    "name": "Martius",
    "chain_id": 121214,
    "rpc_url": "https://martius-i.testnet.romeprotocol.xyz",
    "currency": "rSOL",
    "explorer": "https://romescout-martius-i.testnet.romeprotocol.xyz"
}

class ProxyManager:
    def __init__(self, proxy_file: str = "proxy.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.current_index = 0
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
                print(f"{Fore.GREEN}✓ Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}! No proxies loaded - using direct connection{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error loading proxies: {e}{Style.RESET_ALL}")
    
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
                'https': f'http://{ip}:{port}',
                'display': f"{ip}:{port}"
            }
            if user and password:
                proxy_dict['http'] = f'http://{user}:{password}@{ip}:{port}'
                proxy_dict['https'] = f'http://{user}:{password}@{ip}:{port}'
            return proxy_dict
        except:
            return None
    
    def get_next_proxy(self) -> Optional[Dict]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

class MartianBot:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.current_proxy = None
        self.session = requests.Session()
        self.rotate_proxy()
        self.w3 = self.create_web3_instance()
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
        self.create_files_if_not_exist()
        self.load_accounts()
    
    def create_web3_instance(self):
        if self.current_proxy:
            return Web3(Web3.HTTPProvider(
                NETWORK_CONFIG["rpc_url"],
                session=self.session
            ))
        else:
            return Web3(Web3.HTTPProvider(NETWORK_CONFIG["rpc_url"]))
    
    def rotate_proxy(self):
        self.current_proxy = self.proxy_manager.get_next_proxy()
        if self.current_proxy:
            self.session.proxies = {
                'http': self.current_proxy['http'],
                'https': self.current_proxy['https']
            }
            print(f"{Fore.CYAN}🌐 Using proxy: {self.current_proxy['display']}{Style.RESET_ALL}")
        else:
            self.session.proxies = {}
            print(f"{Fore.YELLOW}🌐 Using direct connection{Style.RESET_ALL}")
        self.w3 = self.create_web3_instance()
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def create_files_if_not_exist(self):
        if not os.path.exists("accounts.txt"):
            with open("accounts.txt", "w") as f:
                f.write("# Add your private keys here (one per line)\n")
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
            print(f"{Fore.RED}✗ Error saving contracts: {e}{Style.RESET_ALL}")
    
    def load_accounts(self):
        try:
            if not os.path.exists("accounts.txt"):
                print(f"{Fore.RED}✗ accounts.txt not found{Style.RESET_ALL}")
                return
            with open("accounts.txt", 'r') as f:
                lines = f.read().strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                private_key = line if line.startswith('0x') else '0x' + line
                try:
                    account = Account.from_key(private_key)
                    self.accounts.append({
                        'private_key': private_key,
                        'address': account.address,
                        'account': account
                    })
                except Exception:
                    continue
            print(f"{Fore.GREEN}✓ Loaded {len(self.accounts)} accounts{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error loading accounts: {e}{Style.RESET_ALL}")
    
    def print_banner(self):
        proxy_info = f"Proxy: {self.current_proxy['display']}" if self.current_proxy else "Direct connection"
        banner = f"""
{Fore.CYAN}╔════════════════════════════════════════════╗
║           🚀 MARTIUS NETWORK BOT 🚀        ║
║             Fixed Version v3.0             ║
╚════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}Network: {NETWORK_CONFIG['name']} ({NETWORK_CONFIG['chain_id']})
Connection: {proxy_info}
Accounts: {len(self.accounts)} loaded{Style.RESET_ALL}
        """
        print(banner)
    
    def print_stats(self):
        print(f"""
{Fore.CYAN}📊 Current Session Stats:{Style.RESET_ALL}
Deployments: {self.stats['successful_deployments']}/{self.stats['total_deployments']}
Transfers: {self.stats['successful_transfers']}/{self.stats['total_transfers']}
        """)
    
    async def get_balance(self, address: str) -> float:
        for attempt in range(3):
            try:
                balance_wei = self.w3.eth.get_balance(address)
                return float(self.w3.from_wei(balance_wei, 'ether'))
            except:
                if attempt < 2:
                    self.rotate_proxy()
                    await asyncio.sleep(1)
                    continue
                return 0.0
    
    def get_detailed_error(self, error) -> str:
        error_str = str(error)
        if 'rome emulate tx failed' in error_str:
            return "Rome network transaction simulation failed - check gas/balance"
        elif 'insufficient funds' in error_str.lower():
            return "Insufficient funds for transaction + gas"
        elif 'nonce too low' in error_str.lower():
            return "Nonce too low - transaction already processed"
        elif 'nonce too high' in error_str.lower():
            return "Nonce too high - future transaction"
        elif 'gas price too low' in error_str.lower():
            return "Gas price too low for network"
        else:
            return error_str[:100] + "..." if len(error_str) > 100 else error_str
    
    async def build_legacy_transaction(self, account: Dict, **params) -> Dict:
        nonce = None
        gas_price = None
        for attempt in range(3):
            try:
                nonce = self.w3.eth.get_transaction_count(account['address'])
                gas_price = self.w3.eth.gas_price
                break
            except:
                if attempt < 2:
                    self.rotate_proxy()
                    await asyncio.sleep(1)
                    continue
                nonce = 0
                gas_price = self.w3.to_wei(1, 'gwei')
        tx_params = {
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': NETWORK_CONFIG['chain_id']
        }
        tx_params.update(params)
        if 'to' in tx_params and tx_params['to']:
            tx_params['to'] = Web3.to_checksum_address(tx_params['to'])
        return tx_params
    
    async def send_transaction_with_retry(self, account: Dict, transaction: Dict, description: str = "transaction") -> Dict:
        for attempt in range(5):
            try:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, account['private_key'])
                raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', None))
                if raw_tx is None:
                    raise Exception("Could not extract raw transaction data")
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)
                    if receipt.status == 1:
                        return {'success': True, 'tx_hash': tx_hash.hex(), 'gas_used': receipt.gasUsed, 'block_number': receipt.blockNumber}
                    else:
                        return {'success': False, 'error': f"Transaction failed - receipt status: {receipt.status}", 'tx_hash': tx_hash.hex()}
                except Exception as receipt_error:
                    return {'success': False, 'error': f"Receipt timeout: {str(receipt_error)[:50]}", 'tx_hash': tx_hash.hex()}
            except Exception as e:
                error_msg = self.get_detailed_error(e)
                if attempt < 4:
                    self.rotate_proxy()
                    await asyncio.sleep(3)
                    try:
                        transaction = await self.build_legacy_transaction(
                            account,
                            to=transaction.get('to', None),
                            value=transaction.get('value', 0),
                            gas=transaction.get('gas', 21000)
                        )
                    except:
                        pass
                    continue
                else:
                    return {'success': False, 'error': error_msg}

    async def transfer_native(self, account: Dict, to_address: str, amount_eth: float):
        self.stats['total_transfers'] += 1
        tx = await self.build_legacy_transaction(
            account,
            to=to_address,
            value=self.w3.to_wei(amount_eth, 'ether'),
            gas=21000
        )
        result = await self.send_transaction_with_retry(account, tx, description=f"Send {amount_eth} {NETWORK_CONFIG['currency']}")
        if result['success']:
            self.stats['successful_transfers'] += 1
            print(f"{Fore.GREEN}✓ {amount_eth} {NETWORK_CONFIG['currency']} sent to {to_address} | TX: {result['tx_hash']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Transfer failed: {result['error']}{Style.RESET_ALL}")
        return result

    async def deploy_contract(self, account: Dict, contract_name: str, constructor_args: list = []):
        self.stats['total_deployments'] += 1
        if contract_name not in CONTRACTS:
            print(f"{Fore.RED}✗ Contract {contract_name} not found in contracts.py{Style.RESET_ALL}")
            return None
        contract_info = CONTRACTS[contract_name]
        contract_bytecode = contract_info.get("bytecode")
        contract_abi = contract_info.get("abi")
        if not contract_bytecode or not contract_abi:
            print(f"{Fore.RED}✗ Invalid contract info for {contract_name}{Style.RESET_ALL}")
            return None
        Contract = self.w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
        tx = await self.build_legacy_transaction(
            account,
            to=None,
            value=0,
            gas=500000
        )
        try:
            tx_data = Contract.constructor(*constructor_args).build_transaction(tx)
            result = await self.send_transaction_with_retry(account, tx_data, description=f"Deploy {contract_name}")
            if result['success']:
                contract_address = self.w3.to_checksum_address(result['tx_hash'][:42])  # Optional: correct method later
                self.deployed_contracts[contract_name] = {
                    'address': contract_address,
                    'deployed_by': account['address'],
                    'tx_hash': result['tx_hash']
                }
                self.save_deployed_contracts()
                self.stats['successful_deployments'] += 1
                print(f"{Fore.GREEN}✓ Contract {contract_name} deployed at {contract_address}{Style.RESET_ALL}")
                return contract_address
            else:
                print(f"{Fore.RED}✗ Deployment failed: {result['error']}{Style.RESET_ALL}")
                return None
        except Exception as e:
            print(f"{Fore.RED}✗ Deployment error: {str(e)[:100]}...{Style.RESET_ALL}")
            return None

    async def interact_with_contract(self, account: Dict, contract_address: str, abi: list, function_name: str, args: list = []):
        self.stats['total_interactions'] += 1
        try:
            contract = self.w3.eth.contract(address=self.w3.to_checksum_address(contract_address), abi=abi)
            func = getattr(contract.functions, function_name)(*args)
            tx_params = await self.build_legacy_transaction(account, to=contract_address, value=0, gas=200000)
            tx_data = func.build_transaction(tx_params)
            result = await self.send_transaction_with_retry(account, tx_data, description=f"Call {function_name}")
            if result['success']:
                self.stats['successful_interactions'] += 1
                print(f"{Fore.GREEN}✓ Function {function_name} executed | TX: {result['tx_hash']}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Interaction failed: {result['error']}{Style.RESET_ALL}")
            return result
        except Exception as e:
            print(f"{Fore.RED}✗ Contract interaction error: {str(e)[:100]}...{Style.RESET_ALL}")
            return None

    async def main_loop(self):
        self.clear_screen()
        self.print_banner()
        while True:
            for account in self.accounts:
                balance = await self.get_balance(account['address'])
                print(f"{Fore.MAGENTA}⚡ {account['address']} balance: {balance} {NETWORK_CONFIG['currency']}{Style.RESET_ALL}")
                # Example: auto-send 0.01 to a predefined address if balance > 0.05
                if balance > 0.05:
                    await self.transfer_native(account, "0xRecipientAddressHere", 0.01)
                # Rotate proxy each account
                self.rotate_proxy()
                await asyncio.sleep(random.randint(3, 7))
            self.print_stats()
            await asyncio.sleep(10)

if __name__ == "__main__":
    bot = MartianBot()
    try:
        asyncio.run(bot.main_loop())
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}\n🚀 Bot stopped by user{Style.RESET_ALL}")
