# BackTest util class.

import backtrader as bt
import backtrader.analyzers as btay
import os
import pandas as pd
import empyrical as ey
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('QT5Agg')

# BackTest is the util class for back test usage basing on backtrader framework.
# For backtrader, see details here: https://www.backtrader.com
# strategy: extended from backtrader.Strategy
# start: start date of back test.
# end: end date of back test.
# dataDir: directory to read the backtest data.
# tickers: tickers code to run the back test(for example, AMZN for Amazon).
# cash: initial cash in the account.
# comission: comission fee of each transaction.
# benchmarkTicker: the code of the benchmark ticker back test by default, set 
#                  to be ^GSPC for SP500.
# drawResult: if true, draw the result diagram.

class BackTest:
    def __init__(self, strategy, start, end, dataDir, tickers, cash = 0.01, 
                 commission = 0.01, benchmarkTicker = "^GSPC", drawResult = False):
        # cerebro will be initialized using _initCerebro.
        self.__cerebro = None
        self.__strategy = strategy
        self.__start = start
        self.__end = end
        self.__dataDir = dataDir
        self.__tickers = tickers
        self.__result = None
        self.__commission = commission
        self.__initcash = cash
        self.__backtestResult = pd.Series()
        self.__returns = pd.Series()
        self.__benchmarkTicker = benchmarkTicker
        self.__benchReturns = pd.Series()
        self.__benchFeed = None
        self.__drawResult = drawResult
        self.__start_date = None
        self.__end_date = None
        self._initCerebro()
        
    # Run back test.
    def run(self):
        self.__backtestResult["initial_cash"] = self.getValue()
        self.__results = self.__cerebro.run()
        self.__backtestResult["end_cash"] = self.getValue()
        self._result()
        if self.__drawResult == True:
            self._drawResult()
        self.__returns = self._timeReturns(self.__results)
        self.__benchReturns = self._getBenchmarkReturns(self.__results)
        self._riskAnaly(self.__returns, self.__benchReturns, self.__backtestResult)
        return self.getResult()
        
    # Return the cash amount.
    def getValue(self):
        return self.__cerebro.broker.getvalue()
        
    # Return the back test result.
    def getResult(self):
        return self.__backtestResult
        
    # Return the return rate of back test trade strategy and the return rate
    # of benchmark ticker for comparison.
    def getReturns(self):
        return self.__returns, self.__benchReturns
        
    # Print backtest result.
    def output(self):
        print("sharpeRatio:", self.__results[0].analyzers.SharpeRatio.get_analysis()["sharperatio"])
        print("annualWinningRate:", self.__results[0].analyzers.AnnualReturn.get_analysis())
        print("maxDrawdown:%.2f，maxDrawdownLen%d" % (self.__results[0].analyzers.DrawDown.get_analysis().max.drawdown, self.__results[0].analyzers.DD.get_analysis().max.len))
        print("returnRate:%.2f" % (self.__results[0].analyzers.Returns.get_analysis()["rtot"]))
            

    # Initialize the Cerebro class of backtrader lib.
    def _initCerebro(self):
        self.__cerebro = bt.Cerebro()
        self.__cerebro.addstrategy(self.__strategy)
        self._createDataFeeds()
        self._settingCerebro()
        
    # Setup Cerebro.
    def _settingCerebro(self):
        # Add drawdown observer.
        self.__cerebro.addobserver(bt.observers.DrawDown)
        # Add benchmark observer.
        self.__cerebro.addobserver(bt.observers.Benchmark, data = self.__benchFeed, timeframe = bt.TimeFrame.NoTimeFrame)
        # Setup comission fee.
        self.__cerebro.broker.setcommission(commission=self.__commission)
        # Setup initial cash.
        self.__cerebro.broker.setcash(self.__initcash)
        # Add metrics need to be analyzed.
        self.__cerebro.addanalyzer(btay.SharpeRatio, _name = "SharpeRatio", riskfreerate = 0.02, stddev_sample = True, annualize = True)
        self.__cerebro.addanalyzer(btay.AnnualReturn, _name = "AnnualReturn")
        self.__cerebro.addanalyzer(btay.DrawDown, _name = "DrawDown")
        self.__cerebro.addanalyzer(btay.Returns, _name = "Returns")
        self.__cerebro.addanalyzer(btay.TradeAnalyzer, _name = "TradeAnalyzer")
        self.__cerebro.addanalyzer(btay.TimeReturn, _name = "TimeReturn")
        self.__cerebro.addanalyzer(btay.TimeReturn, _name = "TimeReturnBenchMark", data = self.__benchFeed)
        self.__cerebro.addanalyzer(btay.SQN, _name = "SQN")
        
    # Create data feed.
    def _createDataFeeds(self):
        for i in range(len(self.__tickers)):
            dataFeed = self._getData(self.__tickers[i])
            feed = bt.feeds.PandasData(dataname=dataFeed)
            self.__cerebro.adddata(feed, name = self.__tickers[i])
        benchFeed = self._getData(self.__benchmarkTicker)
        self.__benchFeed = bt.feeds.PandasData(dataname=benchFeed)
        self.__cerebro.adddata(self.__benchFeed, name = "benchmark")
            
            
    # Calculate winning rate.
    def _winInfo(self, trade_info, result):
        total_trade_num = trade_info["total"]["total"]
        if total_trade_num > 1:
            win_num = trade_info["won"]["total"]
            lost_num = trade_info["lost"]["total"]
            result["transactions"] = total_trade_num
            result["winningRate"] = win_num/total_trade_num
            result["lossingRate"] = lost_num/total_trade_num
        
    # Get back test result.
    def _result(self):
        self.__backtestResult["cash"] = self.getValue()
        self.__backtestResult["totalReturn"] = self.__results[0].analyzers.Returns.get_analysis()["rtot"]
        self.__backtestResult["annualReturn"] = self.__results[0].analyzers.Returns.get_analysis()["rnorm"]
        self.__backtestResult["sharpRatio"] = self.__results[0].analyzers.SharpeRatio.get_analysis()["sharperatio"]
        self.__backtestResult["maxDrawdown"] = self.__results[0].analyzers.DrawDown.get_analysis().max.drawdown
        self.__backtestResult["maxDrawdownLen"] = self.__results[0].analyzers.DrawDown.get_analysis().max.len
        self.__backtestResult["sqn"] = self.__results[0].analyzers.SQN.get_analysis()["sqn"]

        trade_info = self.__results[0].analyzers.TradeAnalyzer.get_analysis()
        self._winInfo(trade_info, self.__backtestResult)
        
    # Get time return.
    def _timeReturns(self, result):
        return pd.Series(result[0].analyzers.TimeReturn.get_analysis())
        
    # Get time return for benchmark.
    def _getBenchmarkReturns(self, result):
        return pd.Series(result[0].analyzers.TimeReturnBenchMark.get_analysis())
        
    # Calculate risky metrics.
    def _riskAnaly(self, returns, benchReturns, results):
        risk = riskAnalyzer(returns, benchReturns)
        result = risk.run()
        results["alpha"] = result["alpha"]
        results["beta"] = result["beta"]
        results["info"] = result["info"]
        results["vola"] = result["vola"]
        results["omega"] = result["omega"]
        results["sortino"] = result["sortino"]
        results["calmar"] = result["calmar"]
        
    # Draw results.
    def _drawResult(self):
        self.__cerebro.plot(iplot=False)
        figname = type(self).__name__+".png"
        plt.savefig(figname)

    # Get data from csv file.
    def _getData(self, ticker):
        fileName = ticker + ".csv"
        filePath = self.__dataDir + fileName
        # If dir not exist, create dir.
        if not os.path.exists(self.__dataDir):
            os.makedirs(self.__dataDir)
        # If file exist, read file.
        if os.path.exists(filePath):
            df = pd.read_csv(filePath)
        else:
        # Get data from yahoo finanical.
            tickerData = yf.Ticker(ticker)
            df = tickerData.history(period='1d', start = self.__start,  end = self.__end)
            df.to_csv(filePath)
            df = pd.read_csv(filePath)
        df.rename(str.lower, axis='columns', inplace=True)
        df.index = pd.to_datetime(df['date'])
        df=df[['open', 'high', 'low', 'close', 'volume']]
        return df
    
   # Initialize the Cerebro class of backtrader lib for opt run. 
    def _InitializeCerebroForOptRun(self, *args, **kwargs):
        self.__cerebro = bt.Cerebro(maxcpus = 1)
        self.__cerebro.optstrategy(self.__strategy, *args, **kwargs)
        self._createDataFeeds()
        self._settingCerebro()
    
    
    # Optimize parameters for the back test strategy. 
    def optRun(self, *args, **kwargs):
        self._InitializeCerebroForOptRun(*args, **kwargs)
        results = self.__cerebro.run()
        testResults = self._optResult(results, **kwargs)
        return testResults
    
    # Get opt run result.
    def _getOptAnalysis(self, result):
        temp = dict()
        temp["cash"] = result[0].analyzers.Returns.get_analysis()["rtot"]
        temp["annualReturn"] = result[0].analyzers.Returns.get_analysis()["rnorm"]
        temp["sharpRatio"] = result[0].analyzers.SharpeRatio.get_analysis()["sharperatio"]
        temp["maxDrawdown"] = result[0].analyzers.DrawDown.get_analysis().max.drawdown
        temp["maxDrawdownLen"] = result[0].analyzers.DrawDown.get_analysis().max.len
        sqn = result[0].analyzers.SQN.get_analysis()["sqn"]
        temp["sqn"] = sqn
        trade_info = result[0].analyzers.TradeAnalyzer.get_analysis()
        self._winInfo(trade_info, temp)
        return temp
        
    # Ger the result of opt run.
    def _optResult(self, results, **kwargs):
        testResults = pd.DataFrame()
        i = 0
        for key in kwargs:
            for value in kwargs[key]:
                temp = self._getOptAnalysis(results[i])
                temp["parameterName"] = key
                temp["parameterValue"] = value
                returns = self._timeReturns(results[i])
                benchReturns = self._getBenchmarkReturns(results[i])
                self._riskAnaly(returns, benchReturns, temp)
                testResults = testResults.append(temp, ignore_index=True)
        return testResults
        

# Calculate risky metrics using empyrical lib.
class riskAnalyzer:
    def __init__(self, returns, benchReturns, riskFreeRate = 0.02):
        self.__returns = returns
        self.__benchReturns = benchReturns
        self.__risk_free = riskFreeRate
        self.__alpha = 0.0
        self.__beta = 0.0
        self.__info = 0.0
        self.__vola = 0.0
        self.__omega = 0.0
        self.__sharpe = 0.0
        self.__sortino = 0.0
        self.__calmar = 0.0
        
    def run(self):
        self._alpha_beta()
        self._info()
        self._vola()
        self._omega()
        self._sharpe()
        self._sortino()
        self._calmar()
        result = pd.Series(dtype = "float64")
        result["alpha"] = self.__alpha
        result["beta"] = self.__beta
        result["info"] = self.__info
        result["vola"] = self.__vola
        result["omega"] = self.__omega
        result["sharp"] = self.__sharpe
        result["sortino"] = self.__sortino
        result["calmar"] = self.__calmar
        return result
        
    def _alpha_beta(self):
        self.__alpha, self.__beta = ey.alpha_beta(returns = self.__returns, factor_returns = self.__benchReturns, risk_free = self.__risk_free, annualization = 1)
        
    def _info(self):
        self.__info = ey.excess_sharpe(returns = self.__returns, factor_returns = self.__benchReturns)
        
    def _vola(self):
        self.__vola = ey.annual_volatility(self.__returns, period='daily')
    
    def _omega(self):
        self.__omega = ey.omega_ratio(returns = self.__returns, risk_free = self.__risk_free)
        
    def _sharpe(self):
        self.__sharpe = ey.sharpe_ratio(returns = self.__returns, annualization = 1)
        
    def _sortino(self):
        self.__sortino = ey.sortino_ratio(returns = self.__returns)
        
    def _calmar(self):
        self.__calmar = ey.calmar_ratio(returns = self.__returns)
        
    
    
