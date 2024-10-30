import quickfix as fix
import logging
import time
import threading
import random
from queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MarketTickerApplication(fix.Application):
    def __init__(self, instruments, initial_prices, log_queue):
        super().__init__()
        self.instruments = instruments
        self.prices = {instrument: price for instrument, price in zip(instruments, initial_prices)}
        self.running = True
        self.log_queue = log_queue  # Queue to send log messages to the client

        # Start price generator in a separate thread
        threading.Thread(target=self.generate_prices, daemon=True).start()

    def generate_prices(self):
        while self.running:
            for instrument in self.instruments:
                self.prices[instrument] += random.uniform(-1, 1)
                time.sleep(1)

    def get_price(self, instrument):
        return self.prices.get(instrument, None)

    def stop(self):
        self.running = False

    def log_message(self, message, level='INFO'):
        log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}"
        logging.info(log_entry)
        self.log_queue.put(log_entry)

    def onCreate(self, sessionID):
        self.log_message(f"Session created: {sessionID}")

    def onLogon(self, sessionID):
        self.log_message(f"Logon successful: {sessionID}")

    def onLogout(self, sessionID):
        self.log_message(f"Logout: {sessionID}")

    def toAdmin(self, message, sessionID):
        pass

    def fromAdmin(self, message, sessionID):
        pass

    def toApp(self, message, sessionID):
        self.log_message(f"Message sent to {sessionID}: {message}")

    def fromApp(self, message, sessionID):
        msg_str = message.toString()
        self.log_message(f"Message received from {sessionID}: {msg_str}")

        try:
            msg_type = message.getHeader().getField(fix.MsgType().getTag())
            self.log_message(f"Received message type: {msg_type}")
        except fix.FieldNotFound as e:
            self.log_message(f"MsgType field not found: {e}", level='ERROR')
            return

        if msg_type == "D":
            try:
                symbol = message.getField(fix.Symbol().getTag())
                quantity = int(message.getField(fix.OrderQty().getTag()))
                self.log_message(f"Received order: {quantity} units of {symbol}")

                price = self.get_price(symbol)
                if price is not None:
                    self.execute_order(symbol, quantity, price, sessionID)
                else:
                    self.log_message(f"Price not available for symbol: {symbol}", level='WARNING')
            except fix.FieldNotFound as e:
                self.log_message(f"Field not found in message: {e}", level='ERROR')

        else:
            self.log_message(f"Message type {msg_type} not processed")
            self.log_message(f"Full message details: {msg_str}")

    def execute_order(self, symbol, quantity, price, sessionID):
        response = fix.Message()
        response.getHeader().setField(fix.BeginString("FIX.4.4"))
        response.getHeader().setField(fix.MsgType("W"))
        response.setField(fix.Symbol(symbol))
        response.setField(fix.LastPx(price))
        response.setField(fix.OrderQty(quantity))
        response.setField(fix.AvgPx(price * quantity))

        fix.Session.sendToTarget(response, sessionID)
        self.log_message(f"Order executed: {quantity} of {symbol} at {price}")
        self.log_message(f"Sent market data response: {response.toString()}")




if __name__ == "__main__":
    instruments = ["EUR/USD", "GBP/USD", "USD/JPY"]
    initial_prices = [150.0, 2800.0, 290.0]

    log_queue = Queue()
    settings = fix.SessionSettings("server.cfg")
    store = fix.FileStoreFactory(settings)
    log = fix.FileLogFactory(settings)
    application = MarketTickerApplication(instruments, initial_prices, log_queue)
    server = fix.SocketAcceptor(application, store, settings, log)

    server.start()
    logging.info("FIX server started.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down the server...")
    finally:
        application.stop()
        server.stop()
