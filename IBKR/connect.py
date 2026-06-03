from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.contract import ComboLeg
from ibapi.tag_value import TagValue
import threading
from threading import Event, Lock
from datetime import datetime, date, timedelta, time, timezone
import time
import warnings
import json
import os

# Mute Warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message="Choices for a categorical distribution.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*weights_only=False.*")

# ================= IBKR Connection =================

_ACCOUNT_SUMMARY_TAGS = (
    "NetLiquidation,TotalCashValue,GrossPositionValue,"
    "UnrealizedPnL,RealizedPnL,AvailableFunds,BuyingPower,"
    "MaintMarginReq,InitMarginReq"
)

class TestApp(EClient, EWrapper):
    """ 
    IBKR Connection to place requests through TWS API
    """

    def __init__(self):
        EClient.__init__(self, self)

        # Order ID
        self.order_id = None
        self.order_id_lock = Lock()

        # Positions
        self.positions = []
        self.positions_ready = Event()

        # Account Summary
        self.account_summary = {}
        self.account_summary_ready = Event()

        # PnL
        self.account_id = None
        self.pnl_data = {}
        self.pnl_ready = Event()

        # News
        self._news_providers = []
        self._news_providers_ready = Event()
        self._conid_cache: dict = {}
        self._conid_result = None
        self._conid_req_id = None
        self._conid_ready = Event()
        self.news_headlines: list = []
        self.news_ready = Event()
        self.news_has_more = False

        # Watchlist
        self.watchlist = self._load_watchlist()

    def nextValidId(self, orderId: int):
        """
        Retrieves initial valid Order ID needed for every IBKR API Call
        """

        self.order_id = orderId
        print(f"Next valid order ID received: {self.order_id}")

    def managedAccounts(self, accountsList: str):
        """
        Callback: called automatically on connect with a comma-separated list of accounts
        """

        self.account_id = accountsList.split(",")[0].strip()
    
    #--------------------- Portfolio Positions ---------------------#

    def get_positions(self):
        """
        Requests all open positions
        """

        self.positions = []  
        self.positions_ready.clear()
        self.reqPositions()  
        self.positions_ready.wait(timeout=10)
        return self.positions

    def position(self, account, contract, position, avgCost):
        """
        Handles each position returned from IBKR
        """

        pos_info = {
            # "account": account,
            "symbol": contract.symbol,
            "conId": contract.conId,
            # "localSymbol": contract.localSymbol,
            "secType": contract.secType,
            "currency": contract.currency,
            "exchange": contract.exchange,
            # "primaryExchange": contract.primaryExchange,
            # "tradingClass": contract.tradingClass,
            "multiplier": contract.multiplier,
            # "lastTradeDateOrContractMonth": contract.lastTradeDateOrContractMonth,
            "position": position,
            "avgCost": avgCost,
            # Optionally:
            # "marketPrice": current_price,
            # "marketValue": current_price * position,
            # "unrealizedPnL": (current_price - avgCost) * position
        }
        if abs(pos_info['position']) > 1e-6:
            self.positions.append(pos_info)
    
    def positionEnd(self):
        """
        End Signal for Position Request
        """

        self.positions_ready.set()

    def print_positions(self):
        """
        Fetches and prints all open positions in a formatted table
        """

        positions = self.get_positions()

        if not positions:
            print("No open positions.")
            return

        col_w = [8, 8, 10, 12]
        header = f"{'Symbol':<{col_w[0]}} {'SecType':<{col_w[1]}} {'Qty':<{col_w[2]}} {'Avg Cost':<{col_w[2]}}"
        print("\n" + header)
        print("-" * (sum(col_w) + 3))
        for p in positions:
            print(
                f"{p['symbol']:<{col_w[0]}} "
                f"{p['secType']:<{col_w[1]}} "
                f"{p['position']:<{col_w[2]}} "
                f"${p['avgCost']:.2f}"
            )
        print()

    #--------------------- Account Summary ---------------------#

    def get_account_summary(self): # -> dict:
        """
        Requests account summary fields from TWS
        """

        with self.order_id_lock:
            order_id = self.order_id
            self.order_id += 1

        self.account_summary = {}
        self.account_summary_ready.clear()
        self.reqAccountSummary(order_id, "All", _ACCOUNT_SUMMARY_TAGS)
        self.account_summary_ready.wait(timeout=10)
        self.cancelAccountSummary(order_id)
        return self.account_summary

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """
        Callback: receives each account summary field
        """

        self.account_summary[tag] = value

    def accountSummaryEnd(self, reqId: int):
        """
        Callback: signals all account summary data has been received
        """

        self.account_summary_ready.set()

    def print_account_summary(self):
        """
        Fetches and prints a formatted account summary
        """

        summary = self.get_account_summary()

        if not summary:
            print("No account summary data received.")
            return

        labels = {
            "NetLiquidation":   "Net Liquidation",
            "TotalCashValue":   "Total Cash",
            "GrossPositionValue": "Gross Position Value",
            "UnrealizedPnL":    "Unrealized P&L",
            "RealizedPnL":      "Realized P&L",
            "AvailableFunds":   "Available Funds",
            "BuyingPower":      "Buying Power",
            "MaintMarginReq":   "Maint. Margin Req.",
            "InitMarginReq":    "Init. Margin Req.",
        }

        print("\nAccount Summary")
        print("-" * 36)
        for tag, label in labels.items():
            if tag in summary:
                try:
                    print(f"  {label:<22}  ${float(summary[tag]):>12,.2f}")
                except ValueError:
                    print(f"  {label:<22}  {summary[tag]:>13}")
        print()

    #--------------------- PnL ---------------------#

    def get_pnl(self) -> dict:
        """
        Requests a single snapshot of account-level P&L from TWS
        """

        if not self.account_id:
            print("Error: account ID not yet received from TWS.")
            return {}

        with self.order_id_lock:
            req_id = self.order_id
            self.order_id += 1

        self.pnl_data = {}
        self.pnl_ready.clear()
        self.reqPnL(req_id, self.account_id, "")
        self.pnl_ready.wait(timeout=10)
        self.cancelPnL(req_id)
        return self.pnl_data

    def pnl(self, _: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        """
        Callback: receives account-level P&L update
        """

        self.pnl_data = {
            "dailyPnL": dailyPnL,
            "unrealizedPnL": unrealizedPnL,
            "realizedPnL": realizedPnL,
        }
        self.pnl_ready.set()

    def print_pnl(self):
        """
        Fetches and prints a formatted P&L summary
        """

        data = self.get_pnl()

        if not data:
            print("No P&L data received.")
            return

        def fmt(val):
            sign = "+" if val >= 0 else "-"
            return f"{sign}${abs(val):,.2f}"

        print("\nP&L Summary")
        print("-" * 30)
        print(f"  {'Daily P&L':<18}  {fmt(data['dailyPnL'])}")
        print(f"  {'Unrealized P&L':<18}  {fmt(data['unrealizedPnL'])}")
        print(f"  {'Realized P&L':<18}  {fmt(data['realizedPnL'])}")
        print()

    #--------------------- News ---------------------#

    def _get_provider_codes(self) -> str:
        """
        Fetches available news provider codes from TWS (cached after first call)
        """

        if self._news_providers:
            return "+".join(self._news_providers)
        self._news_providers_ready.clear()
        self.reqNewsProviders()
        self._news_providers_ready.wait(timeout=5)
        return "+".join(self._news_providers)

    def newsProviders(self, newsProviders):
        """
        Callback: receives available news providers
        """

        self._news_providers = [p.providerCode for p in newsProviders]
        self._news_providers_ready.set()

    def _resolve_conid(self, symbol: str) -> int:
        """
        Resolves the conId for a stock symbol via reqContractDetails (cached)
        """

        symbol = symbol.upper()
        if symbol in self._conid_cache:
            return self._conid_cache[symbol]

        with self.order_id_lock:
            req_id = self.order_id
            self.order_id += 1

        self._conid_result = None
        self._conid_req_id = req_id
        self._conid_ready.clear()
        self.reqContractDetails(req_id, self.create_stock_contract(symbol))
        self._conid_ready.wait(timeout=10)

        if self._conid_result:
            self._conid_cache[symbol] = self._conid_result
        return self._conid_result or 0

    def contractDetails(self, reqId: int, contractDetails):
        """
        Callback: receives contract details; captures conId for news lookups
        """

        if reqId == self._conid_req_id:
            self._conid_result = contractDetails.contract.conId

    def contractDetailsEnd(self, reqId: int):
        """
        Callback: signals all contract details received
        """

        if reqId == self._conid_req_id:
            self._conid_ready.set()

    def historicalNews(self, _: int, time: str, providerCode: str, articleId: str, headline: str):
        """
        Callback: receives a single news headline
        """

        self.news_headlines.append({
            "time": time,
            "provider": providerCode,
            "articleId": articleId,
            "headline": headline,
        })

    def historicalNewsEnd(self, _: int, hasMore: bool):
        """
        Callback: signals all news headlines received
        """

        self.news_has_more = hasMore
        self.news_ready.set()

    def get_news(self, symbol: str, hours: int = 24) -> list:
        """
        Fetches news headlines for a ticker from the last N hours
        """

        conid = self._resolve_conid(symbol)
        if not conid:
            print(f"Error: could not resolve conId for {symbol.upper()}.")
            return []

        provider_codes = self._get_provider_codes()
        if not provider_codes:
            print("Error: no news providers available on this account.")
            return []

        with self.order_id_lock:
            req_id = self.order_id
            self.order_id += 1

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)
        start_str = start.strftime("%Y-%m-%d %H:%M:%S.0")
        end_str = now.strftime("%Y-%m-%d %H:%M:%S.0")

        self.news_headlines = []
        self.news_ready.clear()
        self.reqHistoricalNews(req_id, conid, provider_codes, start_str, end_str, 50, [])
        self.news_ready.wait(timeout=15)
        return self.news_headlines

    def print_news(self, symbol: str, hours: int = 24):
        """
        Fetches and prints news headlines for a ticker from the last N hours
        """

        symbol = symbol.upper()
        headlines = self.get_news(symbol, hours)

        print(f"\nNews: {symbol}  (last {hours}h)")
        print("-" * 52)

        if not headlines:
            print("  No news found.")
            print()
            return

        for item in headlines:
            try:
                dt = datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S.%f")
                time_str = dt.strftime("%m/%d %H:%M")
            except ValueError:
                time_str = item["time"][:16]
            print(f"  [{time_str}] ({item['provider']})  {item['headline']}")

        suffix = "  (more available — raise totalResults)" if self.news_has_more else ""
        print(f"\n  {len(headlines)} headline(s){suffix}")
        print()

    #--------------------- Order Placement ---------------------#

    def create_stock_contract(self, symbol: str, exchange: str = "SMART"): # -> Contract
        """
        Creates a contract for a specified stock symbol
        """

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = "USD"
        return contract
    
    def create_opt_contract(self, symbol: str, strike: float, exp: str, right: str, exchange: str): # -> Contract
        """
        Creates an IBKR Option Contract.

        exp format: 'YYYYMMDD' (e.g. '20260320')
        right: 'C' for Call, 'P' for Put
        """

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = exchange # "PSE", "NASDAQOM", "SMART"
        contract.currency = "USD"

        contract.lastTradeDateOrContractMonth = exp
        contract.strike = strike
        contract.right = right
        contract.multiplier = "100"

        return contract

    def place_limit_order(self, symbol, limit_price, quantity=1):
        """
        Places a simple limit order for the specified symbol
        """

        if self.order_id is None:
            print("Error: Next valid order ID has not been received yet.")
            return

        contract = self.create_stock_contract(symbol)

        with self.order_id_lock:
            order_id = self.order_id
            self.order_id += 1

        myorder = Order()
        myorder.orderId = order_id
        myorder.action = "BUY"
        myorder.orderType = "LMT"
        myorder.lmtPrice = limit_price
        myorder.totalQuantity = quantity
        myorder.tif = "GTC"  
        myorder.eTradeOnly = ''  
        myorder.firmQuoteOnly = ''

        self.placeOrder(order_id, contract, myorder)
        print(f"Placed limit order for {symbol} at {limit_price}")
    
    def place_market_order(self, symbol, quantity=1, action = "BUY"):
        """
        Places a simple market order for the specified symbol
        """

        if self.order_id is None:
            print("Error: Next valid order ID has not been received yet.")
            return

        contract = self.create_stock_contract(symbol)

        with self.order_id_lock:
            order_id = self.order_id
            self.order_id += 1

        myorder = Order()
        myorder.orderId = order_id
        myorder.action = action
        myorder.orderType = "MKT"
        myorder.totalQuantity = quantity
        myorder.tif = "GTC"  
        myorder.eTradeOnly = ''  
        myorder.firmQuoteOnly = '' 

        self.placeOrder(order_id, contract, myorder)

    def place_bracket_order(self, symbol, position, entry_price, take_profit_price, stop_loss_price, quantity=1):
        """
        Places a bracket order (Limit Entry Order, Limit Stop Loss Order, Limit Take Profit Order) for the specified symbol
        """

        if self.order_id is None:
            print("Error: Next valid order ID has not been received yet.")
            return

        contract = self.create_stock_contract(symbol)

        with self.order_id_lock:
            order_id = self.order_id
            self.order_id += 3

        parent_order = Order()
        parent_order.orderId = order_id
        if position == "Long":
            parent_order.action = "BUY"
        else: 
            parent_order.action = "SELL"
        parent_order.orderType = "LMT"
        parent_order.lmtPrice = entry_price
        parent_order.totalQuantity = quantity
        parent_order.tif = "DAY"
        parent_order.transmit = False  
        parent_order.eTradeOnly = ''  
        parent_order.firmQuoteOnly = ''  

       
        take_profit_order = Order()
        take_profit_order.orderId = order_id + 1
        if position == "Long":
            take_profit_order.action = "SELL"
        else: 
            take_profit_order.action = "BUY"
        take_profit_order.orderType = "LMT"
        take_profit_order.lmtPrice = take_profit_price
        take_profit_order.totalQuantity = quantity
        take_profit_order.parentId = parent_order.orderId  
        take_profit_order.transmit = False
        take_profit_order.eTradeOnly = ''
        take_profit_order.firmQuoteOnly = ''

        stop_loss_order = Order()
        stop_loss_order.orderId = order_id + 2
        if position == "Long":
            stop_loss_order.action = "SELL"
        else: 
            stop_loss_order.action = "BUY"
        stop_loss_order.orderType = "STP"
        stop_loss_order.auxPrice = stop_loss_price
        stop_loss_order.totalQuantity = quantity
        stop_loss_order.parentId = parent_order.orderId  
        stop_loss_order.transmit = True 
        stop_loss_order.eTradeOnly = ''
        stop_loss_order.firmQuoteOnly = ''

        self._fill_tracker[order_id] = position
        self._fill_tracker[order_id + 1] = "Exit"
        self._fill_tracker[order_id + 2] = "Exit"

        
        self.placeOrder(parent_order.orderId, contract, parent_order)
        self.placeOrder(take_profit_order.orderId, contract, take_profit_order)
        self.placeOrder(stop_loss_order.orderId, contract, stop_loss_order)
        print(f"Placed bracket {position.upper()} order for {symbol} with entry of {quantity} shares @ ${entry_price}, take profit at {take_profit_price}, and stop loss at {stop_loss_price} with order_IDs {order_id} - {order_id +2}")

    def place_combo_order(self, symbol1, conId1, symbol2, conId2, quantity1=1, quantity2=1, action1="BUY", action2="SELL"):
        """
        Places a combo order with two legs, each identified by its conID
        """

        if self.order_id is None:
            print("Error: Next valid order ID has not been received yet.")
            return

        combo_contract = Contract()
        combo_contract.symbol = symbol1
        combo_contract.secType = "BAG"
        combo_contract.currency = "USD"
        combo_contract.exchange = "SMART"

        leg1 = ComboLeg()
        leg1.conId = conId1
        leg1.ratio = quantity1
        leg1.action = action1
        leg1.exchange = "SMART"

        leg2 = ComboLeg()
        leg2.conId = conId2
        leg2.ratio = quantity2
        leg2.action = action2
        leg2.exchange = "SMART"

        combo_contract.comboLegs = [leg1, leg2]

        with self.order_id_lock:
            order_id = self.order_id
            self.order_id +=1

        combo_order = Order()
        combo_order.orderId = order_id
        combo_order.action = "BUY"
        combo_order.orderType = "MKT"  
        combo_order.totalQuantity = min(quantity1, quantity2)  
        combo_order.eTradeOnly = ''  
        combo_order.firmQuoteOnly = ''  

        self.placeOrder(order_id, combo_contract, combo_order)
        print(f"Placed combo order with {symbol1} ({action1}, {quantity1}) and {symbol2} ({action2}, {quantity2})")
        
    #--------------------- Watchlist ---------------------#

    _WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "watchlist.json")

    def _load_watchlist(self) -> list:
        if not os.path.exists(self._WATCHLIST_PATH):
            return []
        with open(self._WATCHLIST_PATH, "r") as f:
            return json.load(f)

    def _save_watchlist(self):
        with open(self._WATCHLIST_PATH, "w") as f:
            json.dump(self.watchlist, f, indent=2)

    def add_to_watchlist(self, symbol: str):
        symbol = symbol.upper()
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            self._save_watchlist()
            print(f"Added {symbol} to watchlist.")
        else:
            print(f"{symbol} is already in the watchlist.")

    def remove_from_watchlist(self, symbol: str):
        symbol = symbol.upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            self._save_watchlist()
            print(f"Removed {symbol} from watchlist.")
        else:
            print(f"{symbol} not found in watchlist.")

    def print_watchlist(self):
        if not self.watchlist:
            print("Watchlist is empty.")
            return
        print(f"\nWatchlist ({len(self.watchlist)} securities):")
        for i, symbol in enumerate(self.watchlist, start=1):
            print(f"  {i}. {symbol}")
        print()


# ================= Time =================

def did_market_already_close(): 
    eastern = ZoneInfo("America/New_York")
    
    now = datetime.now(eastern)
    market_close = datetime.combine(now.date(), time(16, 15), tzinfo=eastern)
    
    seconds = (market_close - now).total_seconds()
    
    return int(seconds) < 0

def seconds_until_market_close():
    eastern = ZoneInfo("America/New_York")
    
    now = datetime.now(eastern)
    market_close = datetime.combine(now.date(), time(16, 15), tzinfo=eastern)
    
    seconds = (market_close - now).total_seconds()
    
    return max(0, int(seconds))

def seconds_until_market_open():
    eastern = ZoneInfo("America/New_York")
    
    now = datetime.now(eastern)
    market_open = datetime.combine(now.date(), time(9, 30), tzinfo=eastern)
    market_close = datetime.combine(now.date(), time(16, 15), tzinfo=eastern)

    
    wait_open = (market_open - now).total_seconds()
    wait_close = (market_close - now).total_seconds()

    if (wait_open < 0 and wait_close > 0): # Open Market
        return 0
    elif (wait_open > 0): # Pre-Market
        return wait_open
    else: # Post-Market
        tomorrow = now.date() + timedelta(days=1)
        next_open = datetime.combine(tomorrow, time(9, 30), tzinfo=eastern)
        (next_open - now).total_seconds()


# ================= Live Trading =================

def setup_app_and_get_order_id(app, start_trade = False):
    """
    creates a local connection to TWS IBKR through the IBKR Class API
    Retrieves starting ConId
    """

    app.connect("127.0.0.1", 7497, 0)
    app_thread = threading.Thread(target=app.run, daemon=True)
    app_thread.start()

    while app.order_id is None:
        time.sleep(0.1)

    print(f"Main thread received order_id: {app.order_id}")

    return app_thread

# ================= Main Thread =================

def close_IBKR_Connection(app, ib_thread):
    print("Closing IBKR Connection...")
    app.disconnect()    
    ib_thread.join()

def main(): 
    app = TestApp()

    # Creates a listener thread for IBKR API 
    ib_thread = setup_app_and_get_order_id(app, start_trade = True)
    
    app.print_positions()

    app.print_account_summary()

    app.print_pnl()

    time.sleep(5)

    close_IBKR_Connection(app, ib_thread)

if __name__ == "__main__":
    main()

    