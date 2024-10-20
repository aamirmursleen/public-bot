import ccxt
import datetime
import numpy as np
import talib as ta
import time

# Your API credentials
key = ''
secret = ''

# Initialize the MEXC exchange client
exchange = ccxt.mexc({
    'apiKey': key,
    'secret': secret,
    'enableRateLimit': True,
})

# Trading parameters
MARKET_NAME = 'GOAT/USDT'
RSI_THRESHOLD = 31
RSI_CONSECUTIVE = 10
PROFIT_TARGET_PERCENT = 7
STOP_LOSS_PERCENT = 30

# Initialize variables
initial_investment = 0.0
amount_bought = 0.0
first_entry_price = 0.0
rsi_check_counter = 0

# Fetch balance information
balances = exchange.fetch_balance()
base_currency = MARKET_NAME.split('/')[0]   # 'GOAT'
quote_currency = MARKET_NAME.split('/')[1]  # 'USDT'

full_available_to_buy = balances['free'].get(quote_currency, 0)
full_available_to_sell = balances['free'].get(base_currency, 0)

# Check for existing GOAT holdings
if full_available_to_sell > 0:
    amount_bought = full_available_to_sell
    print(f"You have an existing GOAT balance of {amount_bought} GOAT.")

    try:
        initial_rate = float(input("Enter the purchase price (USDT) of your existing GOAT holdings: "))
        initial_investment = amount_bought * initial_rate
        first_entry_price = initial_rate
        print(f"Initial investment: {initial_investment:.2f} USDT at {first_entry_price} USDT/GOAT.\n")
    except ValueError:
        print("Invalid input for initial rate. Exiting.")
        exit()
else:
    print("No existing GOAT holdings detected. The bot will operate normally.\n")

while True:
    try:
        time.sleep(1)  # Wait 1 second between iterations

        # Fetch OHLCV data
        klines = exchange.fetch_ohlcv(symbol=MARKET_NAME, timeframe='1m', limit=100)
        closes = [x[4] for x in klines]

        # Calculate RSI
        the_rsi = ta.RSI(np.array(closes), timeperiod=14)
        current_rsi = the_rsi[-1]
        print(f'The RSI = {current_rsi}')

        # Fetch current price
        ticker = exchange.fetch_ticker(symbol=MARKET_NAME)
        current_price = ticker['bid']
        print(f'Latest GOAT Price: {current_price}')

        # Update balance information
        balances = exchange.fetch_balance()
        full_available_to_buy = balances['free'].get(quote_currency, 0)
        full_available_to_sell = balances['free'].get(base_currency, 0)

        print(f'Available {quote_currency} to buy: {full_available_to_buy}')
        print(f'Available {base_currency} to sell: {full_available_to_sell}\n')

        # Calculate profit
        if amount_bought > 0 and initial_investment > 0:
            current_value = amount_bought * current_price
            profit_usdt = current_value - initial_investment
            target_profit_usdt = 0.07 * initial_investment
            percent_achieved = (profit_usdt / target_profit_usdt) * 100 if target_profit_usdt != 0 else 0
            percent_achieved = min(percent_achieved, 100) if profit_usdt > 0 else 0
            distance_usdt = max(target_profit_usdt - profit_usdt, 0)

            print(f'Current Profit: ${profit_usdt:.2f} USDT')
            print(f'Percent of 7% Profit Target Achieved: {percent_achieved:.2f}%')
            print(f'Distance to 7% Profit Target: ${distance_usdt:.2f} USDT remaining.\n')
        else:
            print('No buy executed yet; profit target not available.\n')

        # Define buy function
        def buy():
            global initial_investment, amount_bought, first_entry_price
            amount_to_spend = full_available_to_buy
            amount = amount_to_spend / current_price
            amount = float(exchange.amount_to_precision(MARKET_NAME, amount))
            if amount > 0:
                order = exchange.create_market_buy_order(symbol=MARKET_NAME, amount=amount)
                print('Buy Order:', order)
                # Record investment details
                initial_investment = amount_to_spend
                amount_bought = amount
                first_entry_price = current_price
            else:
                print('Insufficient USDT to buy after precision adjustment.')

        # Define sell function
        def sell(reason=""):
            global initial_investment, amount_bought, first_entry_price
            amount = float(exchange.amount_to_precision(MARKET_NAME, full_available_to_sell))
            if amount > 0:
                order = exchange.create_market_sell_order(symbol=MARKET_NAME, amount=amount)
                print('Sell Order:', order)
                if reason:
                    print(f'Sell Reason: {reason}')
                # Reset investment details
                initial_investment = 0.0
                amount_bought = 0.0
                first_entry_price = 0.0
            else:
                print('Insufficient GOAT to sell after precision adjustment.')

        # Sell conditions
        if amount_bought > 0 and initial_investment > 0:
            # Profit Target
            if profit_usdt >= target_profit_usdt and full_available_to_sell > 0:
                try:
                    print(f'Profit reached ${profit_usdt:.2f} USDT ({percent_achieved:.2f}% of 7% target). Selling {amount_bought} GOAT.')
                    sell(reason="7% Profit Achieved")

                    with open('MEXC_i_sell.txt', 'a') as text_sell:
                        print('##########################################################\n',
                              f'(RSI = {current_rsi})', 'Time = {datetime.datetime.now()}\n',
                              f'Sell {MARKET_NAME} (Amount Sold = {amount_bought})\n',
                              file=text_sell)
                        print('Sell action recorded.')
                    time.sleep(1)

                except Exception as e:
                    print('Error during sell:', e)
                    with open('sell_error.txt', 'a') as error:
                        print('##########################################################\n',
                              f'(Error = {e})', 'Time = {datetime.datetime.now()}\n',
                              file=error)
                        print('Sell error logged.')
                    time.sleep(1)

            # Stop-Loss
            elif current_price <= 0.7 * first_entry_price and full_available_to_sell > 0:
                try:
                    print(f'Price dropped 30% from purchase. Selling {amount_bought} GOAT to stop loss.')
                    sell(reason="Stop-Loss Triggered")

                    with open('MEXC_i_sell.txt', 'a') as text_sell:
                        print('##########################################################\n',
                              f'(RSI = {current_rsi})', 'Time = {datetime.datetime.now()}\n',
                              f'Sell {MARKET_NAME} (Amount Sold = {amount_bought}) - Stop-Loss Triggered\n',
                              file=text_sell)
                        print('Sell action recorded.')
                    time.sleep(1)

                except Exception as e:
                    print('Error during stop-loss sell:', e)
                    with open('sell_error.txt', 'a') as error:
                        print('##########################################################\n',
                              f'(Error = {e})', 'Time = {datetime.datetime.now()}\n',
                              file=error)
                        print('Sell error logged.')
                    time.sleep(1)

        # Buying condition
        if current_rsi <= RSI_THRESHOLD:
            rsi_check_counter += 1
            if rsi_check_counter >= RSI_CONSECUTIVE and full_available_to_buy > 0:
                try:
                    print(f'RSI has been = {RSI_THRESHOLD} for {RSI_CONSECUTIVE} consecutive checks. Buying {MARKET_NAME}.')
                    buy()

                    with open('MEXC_i_buy.txt', 'a') as text_buy:
                        print('##########################################################\n',
                              f'(RSI = {current_rsi})', f'Time = {datetime.datetime.now()}\n',
                              f'Buy (Amount in {quote_currency} = {initial_investment})\n',
                              file=text_buy)
                        print('Buy action recorded.')
                    time.sleep(1)

                except Exception as r1:
                    print('Error during buy:', r1)
                    with open('buy_error.txt', 'a') as error:
                        print('##########################################################\n',
                              f'(Error = {r1})', f'Time = {datetime.datetime.now()}\n',
                              file=error)
                        print('Buy error logged.')
            else:
                print(f'RSI = {RSI_THRESHOLD} but waiting for confirmation. Counter: {rsi_check_counter}')
                print(f'Current Price during wait: {current_price}\n')
        else:
            rsi_check_counter = 0  # Reset counter if RSI > threshold

    except Exception as general_error:
        print('General Error:', general_error)
        with open('general_error.txt', 'a') as error:
            print('##########################################################\n',
                  f'(Error = {general_error})', f'Time = {datetime.datetime.now()}\n',
                  file=error)
            print('General error logged.')
