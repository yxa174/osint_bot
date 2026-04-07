"""Модуль для поиска по криптовалютным кошелькам."""

import re
import logging
import asyncio

log = logging.getLogger("OSINTBot")


def detect_crypto_address(text: str) -> dict | None:
    """Определяет тип криптовалютного адреса."""
    text = text.strip()

    # BTC (Legacy + SegWit + Native SegWit)
    if re.match(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$", text):
        return {"type": "Bitcoin (BTC)", "currency": "btc", "address": text}
    if re.match(r"^bc1[a-zA-HJ-NP-Z0-9]{25,62}$", text):
        return {"type": "Bitcoin (BTC) SegWit", "currency": "btc", "address": text}

    # ETH / BSC / Polygon и все EVM-совместимые
    if re.match(r"^0x[a-fA-F0-9]{40}$", text):
        return {"type": "EVM (ETH/BSC/Polygon)", "currency": "eth", "address": text}

    # TRX (TRON)
    if re.match(r"^T[a-zA-HJ-NP-Z0-9]{33}$", text):
        return {"type": "TRON (TRX)", "currency": "trx", "address": text}

    # SOL (Solana)
    if re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", text) and not text.startswith(("1", "3")):
        return {"type": "Solana (SOL)", "currency": "sol", "address": text}

    # LTC
    if re.match(r"^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$", text):
        return {"type": "Litecoin (LTC)", "currency": "ltc", "address": text}

    # DOGE
    if re.match(r"^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$", text):
        return {"type": "Dogecoin (DOGE)", "currency": "doge", "address": text}

    # XMR (Monero)
    if re.match(r"^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$", text):
        return {"type": "Monero (XMR)", "currency": "xmr", "address": text}

    return None


async def query_blockchain_btc(address: str) -> dict:
    """Bitcoin — баланс и транзакции через blockchain.info API."""
    result = {}
    try:
        import httpx
        url = f"https://blockchain.info/rawaddr/{address}?limit=0"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "balance_btc": data.get("final_balance", 0) / 1e8,
                    "total_received": data.get("total_received", 0) / 1e8,
                    "total_sent": data.get("total_sent", 0) / 1e8,
                    "n_tx": data.get("n_tx", 0),
                    "first_seen": data.get("time", 0),
                }
    except Exception as e:
        log.debug(f"Blockchain BTC error: {e}")

    return result


async def query_etherscan(address: str, api_key: str) -> dict:
    """Etherscan — баланс ETH и транзакции."""
    result = {}
    if not api_key:
        return result

    try:
        import httpx
        url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={api_key}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "1":
                    balance_wei = int(data.get("result", 0))
                    result["balance_eth"] = balance_wei / 1e18
                    result["balance_wei"] = balance_wei

        # Количество транзакций
        url_tx = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionCount&address={address}&tag=latest&apikey={api_key}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp_tx = await client.get(url_tx)
            if resp_tx.status_code == 200:
                data_tx = resp_tx.json()
                if data_tx.get("result"):
                    result["tx_count"] = int(data_tx["result"], 16)

    except Exception as e:
        log.debug(f"Etherscan error: {e}")

    return result


async def query_tron_api(address: str) -> dict:
    """TRON — баланс и транзакции."""
    result = {}
    try:
        import httpx
        url = f"https://apilist.tronscanapi.com/api/account?address={address}"
        headers = {"TRON-PRO-API-KEY": ""}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                result = {
                    "balance_trx": data.get("balance", 0) / 1e6,
                    "total_tx": data.get("totalTransactionCount", 0),
                    "frozen": data.get("frozen", []),
                    "bandwidth": data.get("bandwidth", {}).get("freeNetLimit", 0),
                    "energy": data.get("energy", 0),
                    "trc20_count": len(data.get("trc20token_balances", [])),
                }
                if data.get("trc20token_balances"):
                    result["trc20_tokens"] = [
                        {
                            "token": t.get("tokenAbbr", t.get("tokenName", "")),
                            "balance": float(t.get("balance", 0)) / (10 ** t.get("tokenDecimal", 0)),
                        }
                        for t in data["trc20token_balances"][:10]
                    ]
    except Exception as e:
        log.debug(f"TRON API error: {e}")

    return result


async def search_crypto_everywhere(address: str) -> str:
    """Полный поиск по криптокошельку."""
    detected = detect_crypto_address(address)
    if not detected:
        return "❌ Не распознан криптокошелёк.\n\nПоддерживаемые:\n• BTC: <code>1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>\n• ETH: <code>0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe</code>\n• TRX: <code>TNQ...<code>\n• SOL: <code>7xKX...<code>"

    import config

    report = f"₿ <b>Поиск по криптокошельку</b>\n\n"
    report += f"💰 <b>Тип:</b> {detected['type']}\n"
    report += f"📍 <b>Адрес:</b> <code>{detected['address']}</code>\n\n"

    api_results = {}

    if detected["currency"] == "btc":
        api_results = await query_blockchain_btc(detected["address"])

        if api_results:
            report += f"📊 <b>Blockchain.info:</b>\n"
            report += f"  💵 Баланс: {api_results.get('balance_btc', 0):.8f} BTC\n"
            report += f"  📥 Получено: {api_results.get('total_received', 0):.8f} BTC\n"
            report += f"  📤 Отправлено: {api_results.get('total_sent', 0):.8f} BTC\n"
            report += f"  🔢 Транзакций: {api_results.get('n_tx', 0)}\n"
        else:
            report += f"⚠️ Нет данных от blockchain.info\n"

    elif detected["currency"] == "eth":
        api_results = await query_etherscan(detected["address"], config.ETHERSCAN_API_KEY)

        if api_results:
            report += f"📊 <b>Etherscan:</b>\n"
            report += f"  💵 Баланс: {api_results.get('balance_eth', 0):.6f} ETH\n"
            report += f"  🔢 Транзакций: {api_results.get('tx_count', 0)}\n"
        else:
            report += f"⚠️ Нет данных (нужен Etherscan API ключ)\n"

    elif detected["currency"] == "trx":
        api_results = await query_tron_api(detected["address"])

        if api_results:
            report += f"📊 <b>TRON:</b>\n"
            report += f"  💵 Баланс: {api_results.get('balance_trx', 0):.2f} TRX\n"
            report += f"  🔢 Транзакций: {api_results.get('total_tx', 0)}\n"
            if api_results.get("trc20_tokens"):
                report += f"  🪙 TRC20 токены:\n"
                for token in api_results["trc20_tokens"][:5]:
                    report += f"    • {token['token']}: {token['balance']}\n"
        else:
            report += f"⚠️ Нет данных от TRON API\n"

    # Ссылки для проверки
    report += f"\n🔎 <b>Проверить на:</b>\n"

    if detected["currency"] == "btc":
        report += f"• <a href=\"https://www.blockchain.com/btc/address/{detected['address']}\">Blockchain.com</a>\n"
        report += f"• <a href=\"https://www.blockchair.com/bitcoin/address/{detected['address']}\">Blockchair</a>\n"
        report += f"• <a href=\"https://mempool.space/address/{detected['address']}\">Mempool</a>\n"
    elif detected["currency"] == "eth":
        report += f"• <a href=\"https://etherscan.io/address/{detected['address']}\">Etherscan</a>\n"
        report += f"• <a href=\"https://debank.com/profile/{detected['address']}\">DeBank</a>\n"
        report += f"• <a href=\"https://www.blockchair.com/ethereum/address/{detected['address']}\">Blockchair</a>\n"
    elif detected["currency"] == "trx":
        report += f"• <a href=\"https://tronscan.org/#/address/{detected['address']}\">Tronscan</a>\n"
        report += f"• <a href=\"https://debank.com/profile/{detected['address']}\">DeBank</a>\n"
    elif detected["currency"] == "sol":
        report += f"• <a href=\"https://solscan.io/account/{detected['address']}\">Solscan</a>\n"
        report += f"• <a href=\"https://explorer.solana.com/address/{detected['address']}\">Solana Explorer</a>\n"

    report += "\n\n💡 <i>Данные из открытых блокчейн-API</i>"

    return report
