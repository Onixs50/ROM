# Rome Martius Deployer

- Network: Martius (Chain ID 121214, symbol rSOL)
- Default RPC: https://martius-i.testnet.romeprotocol.xyz

## Files
- contracts.sol : 10 interactable contracts.
- bot.py : The deploy & interact CLI.
- requirements.txt : Python dependencies.
- account.txt : Put your accounts (private keys) here.
- proxy.txt : Optional proxies, any common format.

## Quickstart (Ubuntu)
```bash
git clone https://github.com/Onixs50/ROM.git
cd ROM
pip3 install -r requirements.txt
python3 bot.py

sudo apt-get update

python3 -m venv .venv
source .venv/bin/activate

python3 -c "from solcx import install_solc; install_solc('0.8.24')"
python3 bot.py
```

During runtime, the bot asks for:
- RPC URL (default is Martius)
- Mode (random/manual)
- Counts (deployments & interactions per contract)
- Delays (min/max seconds between tx)
- Whether to use a proxy from proxy.txt

It prints every tx status in color and ends with a per-wallet summary table.
