# Turtle strategy

import backtrader as bt
import backtrader.indicators as bi
import backtest as backtest
import math
import holidays 
import matplotlib
matplotlib.use('QT5Agg')


class TurtleStrategy(bt.Strategy):
    params = (
        ("period", 20),
        ("atr", 14),
        ("printlog", False),
    )
   
    def __init__(self):
        self.order = None
        self.buyprice = 0
        self.comm = 0
        self.buy_size = 0
        self.buy_count = 0
  
        self.H_line = bi.Highest(self.data.high(-1), period = self.p.period)
        self.L_line = bi.Lowest(self.data.low(-1), period = self.p.period)
        self.TR = bi.Max((self.data.high(0) - self.data.low(0)), abs(self.data.close(-1) - self.data.high(0)), abs(self.data.close(-1) - self.data.low(0)))
        self.ATR = bi.SimpleMovingAverage(self.TR, period = self.p.atr)

        self.buy_signal = bt.ind.CrossOver(self.data.close(0), self.H_line)
        self.sell_signal = bt.ind.CrossOver(self.data.close(0), self.L_line)
        self.us_holidays = holidays.UnitedStates()
       
    def next(self):
        if self.order:
            return
        if  self.us_holidays or self.datas[0].datetime.date(0).weekday() >= 5:
            return

        if self.buy_signal > 0 and self.buy_count == 0:
            self.buy_size = math.ceil((self.broker.getvalue() * 0.01 / self.ATR) / 100) * 100
            self.sizer.p.stake = self.buy_size
            self.buy_count = 1
            self.order = self.buy()
            self.log("buy")
           
        elif self.data.close > self.buyprice + 0.5*self.ATR[0] and self.buy_count > 0 and self.buy_count <= 4:
            self.buy_size = math.ceil((self.broker.get_cash() * 0.01 / self.ATR) / 100) * 100
            self.sizer.p.stake = self.buy_size
            self.order = self.buy()
            self.buy_count += 1
            self.log("buy")
           
        elif self.sell_signal < 0 and self.buy_count > 0:
            self.order = self.sell()
            self.buy_count = 0
            self.log("sell")
           
        elif self.data.close < (self.buyprice - 2*self.ATR[0]) and self.buy_count > 0:
            self.order = self.sell()
            self.buy_count = 0
            self.log("sell")
           
           
    def log(self, txt, dt = None, doprint = False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))
           
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'buy with prize: %.2f, value: %.2f, comission: %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                self.buyprice = order.executed.price
                self.comm += order.executed.comm
            else:
                self.log(
                    'sell with priz: %.2f, value: %.2f, comission: %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                self.comm += order.executed.comm
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("transaction fail")
        self.order = None
               
        
if __name__ == "__main__":
    cerebro = bt.Cerebro()
                
    start = "2020-10-01"
    end = "2021-10-21"
    ticker = ["AAPL"]
    backtest = backtest.BackTest(TurtleStrategy, start, end, 
                                 "./data/", 
                                 ticker, cash=30000, drawResult = False)
    result = backtest.run()
    print(result)
#   resultOpt = backtest.optRun(period = range(10, 50), atr = range(10, 20))
#   print(resultOpt)
    