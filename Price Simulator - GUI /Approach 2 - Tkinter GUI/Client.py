import tkinter as tk
from tkinter import ttk
import quickfix as fix
import logging
import random
import time
from datetime import datetime
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketTickerApplication(fix.Application):
    def __init__(self, instruments, initial_prices, message_callback):
        super().__init__()
        self.instruments = instruments
        self.prices = {instrument: price for instrument, price in zip(instruments, initial_prices)}
        self.running = True
        self.message_callback = message_callback
        self.lock = threading.Lock() 

        # Start price generator in a separate thread
        threading.Thread(target=self.generate_prices, daemon=True).start()

    def generate_prices(self):
        while self.running:
            with self.lock:
                for instrument in self.instruments:
                    self.prices[instrument] += random.uniform(-1, 1)
            time.sleep(1)

    def get_price(self, instrument):
        with self.lock:
            return self.prices.get(instrument, None)

    def stop(self):
        self.running = False

    def onCreate(self, sessionID):
        logging.info(f"Session created: {sessionID}")

    def onLogon(self, sessionID):
        logging.info(f"Logon successful: {sessionID}")

    def onLogout(self, sessionID):
        logging.info(f"Logout: {sessionID}")

    def toAdmin(self, message, sessionID):
        pass 

    def fromAdmin(self, message, sessionID):
        pass 

    def toApp(self, message, sessionID):
        self.message_callback(message.toString(), 'Client')
        logging.info(f"Message sent to {sessionID}: {message}")

    def fromApp(self, message, sessionID):
        msg_str = message.toString()
        self.message_callback(msg_str, 'Server')
        logging.info(f"Message received from {sessionID}: {msg_str}")

        msg_type = message.getHeader().getField(fix.MsgType())
        logging.info(f"Processing message type: {msg_type}")

        if msg_type == fix.MsgType().MarketDataSnapshotFullRefresh:
            symbol = message.getField(fix.Symbol())
            price = message.getField(fix.LastPx())
            with self.lock:
                self.prices[symbol] = price
            self.message_callback(f"Price update: {symbol} is now {price:.2f}", 'Server')

        elif msg_type == fix.MsgType().ExecutionReport:
            order_id = message.getField(fix.ClOrdID())
            exec_type = message.getField(fix.ExecType())
            ord_status = message.getField(fix.OrdStatus())
            symbol = message.getField(fix.Symbol())
            self.message_callback(f"Order {order_id} executed. Status: {ord_status} ({exec_type}) for {symbol}", 'Server')

            # Logging the message in the specified format for server messages
            logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} - INFO - {msg_str}")

        else:
            self.message_callback(f"Received unhandled message type: {msg_type}", 'Server')

    def send_order(self, message):
                session_id = fix.SessionID("FIX.4.4", "CLIENT", "MARKET_MAKER")  
                fix.Session.sendToTarget(message, session_id)
            

class ClientApp:
    def __init__(self):
        self.instruments = ["EUR/USD", "GBP/USD", "USD/JPY"]
        self.initial_prices = [150.0, 2800.0, 290.0]

        self.market_app = MarketTickerApplication(self.instruments, self.initial_prices, self.log_message)

        self.settings = fix.SessionSettings("client.cfg")
        self.store = fix.FileStoreFactory(self.settings)
        self.log = fix.FileLogFactory(self.settings)
        self.initiator = fix.SocketInitiator(self.market_app, self.store, self.settings, self.log)

        self.initiator.start()

        self.root = tk.Tk()
        self.root.title("Market Data Client")

        self.heading = tk.Label(self.root, text="Market Data Streaming", font=("Arial", 16))
        self.heading.pack(pady=10)

        self.price_labels = {}
        for instrument in self.instruments:
            label = tk.Label(self.root, text=f"{instrument}: --")
            label.pack()
            self.price_labels[instrument] = label

        self.create_order_section()
        self.create_message_log_section()

        self.root.after(1000, self.update_prices)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_order_section(self):
        order_frame = ttk.LabelFrame(self.root, text="Place Order")
        order_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.instrument_var = tk.StringVar(value="EUR/USD")
        self.instrument_combo = ttk.Combobox(order_frame, textvariable=self.instrument_var, values=self.instruments)
        self.instrument_combo.pack(pady=5)

        self.quantity_entry = ttk.Entry(order_frame, width=10)
        self.quantity_entry.pack(pady=5)
        self.quantity_entry.insert(0, "Quantity")

        self.order_type_var = tk.StringVar(value="Market")
        self.order_type_combo = ttk.Combobox(order_frame, textvariable=self.order_type_var, values=["Market", "Limit"])
        self.order_type_combo.pack(pady=5)

        self.price_entry = ttk.Entry(order_frame, width=10)
        self.price_entry.pack(pady=5)
        self.price_entry.insert(0, "Price (if Limit)")

        self.side_var = tk.StringVar(value="Buy")
        self.side_combo = ttk.Combobox(order_frame, textvariable=self.side_var, values=["Buy", "Sell"])
        self.side_combo.pack(pady=5)

        self.place_order_button = ttk.Button(order_frame, text="Place Order", command=self.place_order)
        self.place_order_button.pack(pady=5)

    def create_message_log_section(self):
        log_frame = ttk.LabelFrame(self.root, text="Message Logs")
        log_frame.pack(padx=10, pady=10, fill="both", expand=True)

        ttk.Label(log_frame, text="Client Messages").pack()
        self.client_log = tk.Text(log_frame, wrap=tk.WORD, height=5)
        self.client_log.pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="Server Messages").pack()
        self.server_log = tk.Text(log_frame, wrap=tk.WORD, height=5)
        self.server_log.pack(fill=tk.BOTH, expand=True)

    def update_prices(self):
        for instrument in self.instruments:
            price = self.market_app.get_price(instrument)
            if price is not None:
                self.price_labels[instrument].config(text=f"{instrument}: {price:.2f}")
        self.root.after(1000, self.update_prices)

    def place_order(self):
        instrument = self.instrument_var.get()
        order_type = self.order_type_var.get()
        side = self.side_var.get()
        try:
            quantity = float(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError("Quantity must be positive.")
        except ValueError:
            self.log_message("Invalid quantity. Please enter a valid number.", 'Client')
            return

        price = self.price_entry.get() if order_type == "Limit" else ""

        # Create a FIX message
        message = fix.Message()
        message.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        message.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))

        message.setField(fix.ClOrdID(str(random.randint(100000, 999999))))
        message.setField(fix.Symbol(instrument))
        message.setField(fix.Side(fix.Side_BUY if side == "Buy" else fix.Side_SELL))
        message.setField(fix.OrderQty(quantity))

        transact_time = datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]
        transact_time_field = fix.TransactTime()
        transact_time_field.setString(transact_time)
        message.setField(transact_time_field)

        if order_type == "Limit":
            try:
                price = float(price)
                message.setField(fix.Price(price))
            except ValueError:
                self.log_message("Invalid price. Please enter a valid number for Limit orders.", 'Client')
                return
            message.setField(fix.OrdType(fix.OrdType_LIMIT))

            # Simulate the server message for limit order placement
            order_received_message = (
                "8=FIX.4.4\x01"
                "9=117\x01"  # Length of message
                "35=D\x01"  # New Order - Single
                "34=3\x01"  # Message sequence number
                "49=MARKET_MAKER\x01"
                f"52={datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]}\x01"
                "56=CLIENT\x01"
                f"11={message.getField(fix.ClOrdID())}\x01"  # Use ClOrdID from the order
                f"38={quantity}\x01"  # Order quantity
                f"40=2\x01"  # Order type (2 = Limit)
                "54=1\x01"  # Side (1 = Buy)
                f"55={instrument}\x01"
                f"60={datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]}\x01"
                f"44={price}\x01"  # Limit price
                "10=105"  # Checksum
            )
            receipt_msg_type = f"Received message type: W"  # Change message type to W
        else:
            message.setField(fix.OrdType(fix.OrdType_MARKET))

            # Simulate the server message for market order placement
            order_received_message = (
                "8=FIX.4.4\x01"
                "9=123\x01"  # Length of message
                "35=D\x01"  # New Order - Single
                "34=2\x01"  # Message sequence number
                "49=CLIENT\x01"
                f"52={datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]}\x01"
                "56=MARKET_MAKER\x01"
                f"11={random.randint(10000000, 99999999)}\x01"  # Random ClOrdID
                f"38={quantity}\x01"
                "40=1\x01"  # Order type (1 = Market)
                "54=1\x01"  # Side (1 = Buy)
                f"55={instrument}\x01"
                f"60={datetime.utcnow().strftime('%Y%m%d-%H:%M:%S.%f')[:-3]}\x01"
                "10=105"  # Checksum
            )
            receipt_msg_type = f"Received message type: D"  # Keep message type as D for market orders

        # Send the order
        self.market_app.send_order(message)

        # Log the client message
        order_details = f"Order placed: {side} {quantity} of {instrument} at {'Market' if order_type == 'Market' else price}"
        self.log_message(order_details, 'Client')

        # Log the received message and details in the UI
        self.log_message(receipt_msg_type, 'Server')  # Log message type in UI
        self.log_message(order_received_message, 'Server')  # Log received order in UI

        if order_type == "Limit":
            executed_order_msg = f"Order executed: {quantity} of {instrument} at {price}"
            self.log_message(executed_order_msg, 'Server')  # Log executed order message in UI


    def log_message(self, msg, source):
        self.root.after(0, self._safe_log, msg, source)

    def _safe_log(self, msg, source):
        if source == 'Client':
            self.client_log.insert(tk.END, msg + '\n')
            self.client_log.see(tk.END)
        else:
            self.server_log.insert(tk.END, msg + '\n')
            self.server_log.see(tk.END)

    def on_close(self):
        self.market_app.stop()
        self.initiator.stop()
        self.root.quit()

if __name__ == "__main__":
    app = ClientApp()
    app.root.mainloop()
