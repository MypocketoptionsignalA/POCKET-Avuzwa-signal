//+------------------------------------------------------------------+
//|                                                  AlgoNovaEA.mq5  |
//|                      Professional MT5 EA v6                     |
//+------------------------------------------------------------------+
#property copyright "Grok Algo Nova EA"
#property version   "6.00"
#property strict

input double   LotSize             = 0.01;      
input int      TakeProfit          = 80;        
input int      StopLoss            = 40;        
input int      MagicNumber         = 202506;    
input int      Slippage            = 30;        

bool TradingEnabled = true;

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("🚀 ALGO NOVA EA v6 Started Successfully");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!TradingEnabled) return;
   if(PositionsTotal() > 0) return;

   double ema9  = iMA(_Symbol, PERIOD_M5, 9,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ema21 = iMA(_Symbol, PERIOD_M5, 21, 0, MODE_EMA, PRICE_CLOSE, 1);

   double close1 = Close[1];

   // BUY SIGNAL
   if(ema9 > ema21 && Close[2] <= ema21 && close1 > ema9)
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = ask - StopLoss * _Point;
      double tp = ask + TakeProfit * _Point;

      OrderSend(_Symbol, OP_BUY, LotSize, ask, Slippage, sl, tp, "AlgoNova BUY", MagicNumber, 0, clrGreen);
   }

   // SELL SIGNAL
   if(ema9 < ema21 && Close[2] >= ema21 && close1 < ema9)
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = bid + StopLoss * _Point;
      double tp = bid - TakeProfit * _Point;

      OrderSend(_Symbol, OP_SELL, LotSize, bid, Slippage, sl, tp, "AlgoNova SELL", MagicNumber, 0, clrRed);
   }
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("ALGO NOVA EA v6 Stopped");
}
