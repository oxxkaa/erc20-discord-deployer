import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import telethon 
from telethon import TelegramClient, events
import time
import websockets
import json
from web3 import Web3
from solcx import compile_standard, install_solc
import requests
from typing import Optional
from discord import Embed
from discord.ui import Button, View
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import telethon 
from telethon import TelegramClient, events
import logging
import sys
import sqlite3
import re
from discord import Intents
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time



#TELEGRAM ID --> https://docs.telethon.dev/en/stable/ 
api_id = #'api_id'
api_hash = #'api_hash'
telegram_client = TelegramClient('anon', api_id, api_hash)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)
#Solidity version
install_solc('0.8.23')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    await bot.tree.sync()


#LOCK LP 
@bot.tree.command(name="lock")
@app_commands.describe(name="name of token", token_address="address token", private_keys="dev private key")
async def lock(interaction: discord.Interaction, name: str, token_address: str, private_keys: str):
    await interaction.response.defer(ephemeral=True)
    # for provider ---> https://www.alchemy.com/
    w3 = Web3(Web3.HTTPProvider('https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY'))

    # middleware for l2 
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    # change for uniswap if using mainet
    quickswap_factory_address = '0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32'
    # change for weth if using mainet 
    wmatic_address = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'
    
    # Change with uniswap abi factory if using mainet 
    with open('QuickswapFactory.json', 'r') as file:
        quickswap_factory_abi = json.load(file)

    
    quickswap_factory_contract = w3.eth.contract(address=quickswap_factory_address, abi=quickswap_factory_abi)

    # Appel de la fonction getPair avec l'adresse du token et l'adresse du WMATIC
    pair_address = quickswap_factory_contract.functions.getPair(token_address, wmatic_address).call()
    # Obtention de l'adresse à partir de la clé privée
    account = w3.eth.account.from_key(private_keys)
    account_address = account.address

    # Pair quickswap ABI 
    with open('UniswapV2Pair.json', 'r') as file:
        univ2_pair_abi = json.load(file)

    univ2_pair_contract = w3.eth.contract(address=pair_address, abi=univ2_pair_abi)

    balance = univ2_pair_contract.functions.balanceOf(account_address).call()

    readable_balance = w3.from_wei(balance, 'ether')

    # ABI of UNCX token lock 
    with open('UNCX.json', 'r') as file:
        uncx_abi = json.load(file)

    uncx_contract_address = '0xC9045b0334485E5B62AC545bb86304C32806FD26'

    uncx_contract = w3.eth.contract(address=uncx_contract_address, abi=uncx_abi)

    account = w3.eth.account.from_key(private_keys)
    account_address = account.address

    with open('UniswapV2Pair.json', 'r') as file:
        univ2_pair_abi = json.load(file)

    univ2_pair_contract = w3.eth.contract(address=pair_address, abi=univ2_pair_abi)

    balance = univ2_pair_contract.functions.balanceOf(account_address).call()

    approve_txn = univ2_pair_contract.functions.approve(
        uncx_contract_address, 
        balance
    ).build_transaction({
        'from': account_address,
        'nonce': w3.eth.get_transaction_count(account_address),
        'gas': 50000, #You can change this if you want , not perfect use of gas 
        'gasPrice': w3.eth.gas_price
    })

    signed_approve_txn = w3.eth.account.sign_transaction(approve_txn, private_key=private_keys)


    approve_txn_hash = w3.eth.send_raw_transaction(signed_approve_txn.rawTransaction)

    w3.eth.wait_for_transaction_receipt(approve_txn_hash)

    nonce = w3.eth.get_transaction_count(account_address)
    gas_price = w3.eth.gas_price
    lock_txn = uncx_contract.functions.lockLPToken(
        pair_address,
        balance,
        int(time.time()) + 60*60*24*30,
        account_address
    ).build_transaction({
        'from': account_address,
        'nonce': nonce,
        'gas': 600000,
        'gasPrice': gas_price,
    })

    signed_txn = w3.eth.account.sign_transaction(lock_txn, private_key=private_keys)

    try:
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash)
    except Exception as e:
        print(f"Error: {e}")



@bot.tree.command(name="verif")
@app_commands.describe(name="name token", token_address="address token", tweet="link tweet", telegram="link telegram")
async def launch(interaction: discord.Interaction, name: str, token_address: str, tweet: str, telegram: str):
    await interaction.response.defer(ephemeral=True)
    #Your etherscan or polyscan ... other explorer api keys --> log in in explorer and get a key
    apikey= "KEY"
    #YOUR SOL TOKEN CONTRACT
    contract_name = f"{name}.sol"
    try:
        with open(contract_name, 'r') as file:
            source_code = file.read()
            source_code = source_code.replace("https://t.me/", telegram)
            source_code = source_code.replace("https://twitter.com/", tweet)
    except FileNotFoundError:
        await interaction.followup.send(f"Error : File {contract_name} not found.")
        return

    compiler_version= "v0.8.23+commit.f704f362"
    license_type= 2
    optimization_used= 0


    data = {
        'apikey': apikey,
        'module': 'contract',
        'action': 'verifysourcecode',
        'contractaddress': token_address,
        'sourceCode': source_code,
        'codeformat': 'solidity-single-file',
        'contractname': name,
        'compilerversion': compiler_version,
        'optimizationUsed': optimization_used,
        'constructorArguements': '',
        'evmversion': '',
        'licenseType': license_type
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    #CHANGE IF YOU USE OTHER NETWORK AND EXPLORER
    response = requests.post("https://api.polygonscan.com/api", data=data, headers=headers)
    result = response.json()
    print(f"Réponse d'Etherscan: {result}")
    if result['status'] == '1':
        await interaction.followup.send(f"Verification submitted successfully. GUID: {result['result']}")
    else:
        error_message = f"Error submitting verification: {result.get('message', 'No message')}; Result: {result.get('result', 'No result')}"
        print(error_message)
        await interaction.followup.send(f"Error submitting verification: {result['message']}")
    

    guid= (f"{result['result']}")
    params = {
        'apikey': apikey,
        'guid': guid,
        'module': "contract",
        'action': "checkverifystatus"
    }

    response = requests.get("https://api.polygonscan.com/api", params=params)
    result = response.json()


@bot.tree.command(name="launch")
@app_commands.describe(name="token name", token_address="address token", private_keys="dev private key")
async def launch(interaction: discord.Interaction, name: str, token_address: str, private_keys: str):
    await interaction.response.defer(ephemeral=True)
    w3 = Web3(Web3.HTTPProvider('https://polygon-mainnet.g.alchemy.com/v2/KEY'))
    # Again middleware :)
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    account = w3.eth.account.from_key(private_keys)
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    eth_transfer_txn = {
        'from': account.address,
        'to': token_address,
        'value': w3.to_wei(1, 'ether'),
        'nonce': nonce,
        'gas': 25000,
        'gasPrice': gas_price,
        'chainId': 137 #CHANGE WITH CHAINID ----> https://chainlist.org/ 
    }
    gas_estimate = w3.eth.estimate_gas(eth_transfer_txn)
    eth_transfer_txn['gas'] = gas_estimate


    try:
        signed_eth_txn = w3.eth.account.sign_transaction(eth_transfer_txn, private_key=private_keys)
        txn_hash = w3.eth.send_raw_transaction(signed_eth_txn.rawTransaction)
    except ValueError as e:
        print(f"Error w/ tx: {e}")
    with open(f"{name}_ABI.json", 'r') as abi_file:
        abi = json.load(abi_file)
    token_contract = w3.eth.contract(address=token_address, abi=abi)
    token_transfer_txn = token_contract.functions.transfer(token_address, 100000000000000000000).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address) + 1,
    })
    signed_token_txn = w3.eth.account.sign_transaction(token_transfer_txn, private_key=private_keys)
    w3.eth.send_raw_transaction(signed_token_txn.rawTransaction)
  
    opentxn = token_contract.functions.openTrading().build_transaction({
        'from': account.address,
        'gas': 2900000,
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account.address) + 2,
    })

    try:
        signed_txn = w3.eth.account.sign_transaction(opentxn, private_key=private_keys)
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    except ValueError as e:
        print(f"Error send tx: {e}")

    estimated_gas_for_remove_limits = w3.eth.estimate_gas({
        'from': account.address,
    })

    remove_limits_txn = token_contract.functions.removeLimits().build_transaction({
        'gas': 38000,
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account.address) + 3,
    })  

    try:
        signed_remove_limits_txn = w3.eth.account.sign_transaction(remove_limits_txn, private_key=private_keys)
        remove_limits_txn_hash = w3.eth.send_raw_transaction(signed_remove_limits_txn.rawTransaction)
    except ValueError as e:
        print(f"Error: {e}")

    estimated_gas_for_renounce_ownership = w3.eth.estimate_gas({
        'from': account.address,
    })

    renounce_ownership_txn = token_contract.functions.renounceOwnership().build_transaction({
        'gas': 30000,
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account.address) + 4,
    })


    try:
        signed_renounce_ownership_txn = w3.eth.account.sign_transaction(renounce_ownership_txn, private_key=private_keys)
        renounce_ownership_txn_hash = w3.eth.send_raw_transaction(signed_renounce_ownership_txn.rawTransaction)       
    except ValueError as e:
        print(f"Error: {e}")



@bot.tree.command(name="create_token")
@app_commands.describe(ticker="ticker of token $TOKEN", name="name of token", private_keys="dev private key")
async def create_token(interaction: discord.Interaction, ticker: str, name: str, private_keys: str):
    await interaction.response.defer(ephemeral=True)
    try:
        with open('token_contract.sol', 'r') as file:
            contract_content = file.read()
            contract_content = contract_content.replace("PAULTOSHI", name)
            contract_content = contract_content.replace("unicode\"NAME\"", f"unicode\"{name}\"")
            contract_content = contract_content.replace("unicode\"TICKER\"", f"unicode\"{ticker}\"")
        
        new_file_name = f"{name}.sol"
        with open(new_file_name, 'w') as new_file:
            new_file.write(contract_content)
        compiled_sol = compile_standard({
            "language": "Solidity",
            "sources": {new_file_name: {"content": contract_content}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                    }
                }
            }
        }, solc_version='0.8.23')

        contract_name = name 
        contract_key = f"{new_file_name}:{contract_name}" 
        abi = compiled_sol['contracts'][new_file_name][contract_name]['abi']
        bytecode = compiled_sol['contracts'][new_file_name][contract_name]['evm']['bytecode']['object']

        abi_str = json.dumps(abi, indent=2)
        if len(abi_str) > 2000: 
            with open(f"{name}_ABI.json", 'w') as abi_file:
                json.dump(abi, abi_file)
        else:
            await interaction.followup.send(f"```json\n{abi_str}\n```")

        with open(f"{name}_compiled.json", 'w') as compiled_file:
            json.dump(compiled_sol, compiled_file)
        
        w3 = Web3(Web3.HTTPProvider('https://polygon-mainnet.g.alchemy.com/v2/KEY'))
        print(w3.is_connected()) 
        
        account = w3.eth.account.from_key(private_keys)
        BUILDER = w3.eth.contract(abi=abi, bytecode=bytecode)
        bytecode_bytes = bytes.fromhex(bytecode)
        gas_price = w3.eth.gas_price
        constructor_tx = BUILDER.constructor().build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': gas_price,
        })

        gas_estimate = w3.eth.estimate_gas(constructor_tx)
        constructor_tx['gas'] = gas_estimate
        signed_tx = account.sign_transaction(constructor_tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = await asyncio.get_event_loop().run_in_executor(None, lambda: w3.eth.wait_for_transaction_receipt(tx_hash))
        await interaction.followup.send(f"CA : {tx_receipt.contractAddress} ")
        await interaction.followup.send(f"Name : {contract_name} ")
        await interaction.followup.send(f"Private Keys : {private_keys} ")

        # FOR SNIPE YOUR OWN TOKEN WITH BANANA
        erc20_address = (f"{tx_receipt.contractAddress}")
        amount = 0.01
        tips = 0.01
        wallet_number = 1

        async with telegram_client:
            await telegram_client.send_message('@BananaGunSniper_bot', '/start')
            await asyncio.sleep(1)

            messages = await telegram_client.get_messages('@BananaGunSniper_bot', limit=1)
            if messages:
                last_message = messages[0]
                button_clicked = False
                for row in last_message.buttons:
                    for button in row:
                        if button.text == "🍌 Auto Sniper":
                            await button.click()
                            button_clicked = True
                            await asyncio.sleep(1)
                            break
                    if button_clicked:
                        break
                if button_clicked:
                    await telegram_client.send_message('@BananaGunSniper_bot', erc20_address)
                    await asyncio.sleep(3)
                    messages = await telegram_client.get_messages('@BananaGunSniper_bot', limit=1)
                    if messages:
                        last_message = messages[0]
                        await telegram_client.send_message('@BananaGunSniper_bot', f'{amount}/{tips}/{wallet_number}', reply_to=last_message.id)
                    else:
                        print("No message from '@BananaGunSniper_bot'")
                else:
                    print("Bouton '🍌 Auto Sniper' not found")


    except FileNotFoundError:
        print("File token_contract.sol not found.")


bot.run(YOUR_DISCORD_TOKEN)
