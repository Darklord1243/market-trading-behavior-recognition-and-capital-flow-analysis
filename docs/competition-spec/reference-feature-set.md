# Reference Feature Set (§3.1)

> Official competition spec field list — **89 fields**. Participants compute these from raw L2;
> the organizers do **not** ship this as a downloadable table (see project brief §2).

| Field | 中文说明 | English description |
|---|---|---|
| `date` | 日期 | Date |
| `symbol` | 股票代码 | Stock Code |
| `window_start` | 窗口开始时间 | Window Start Time |
| `window_end` | 窗口结束时间 | Window End Time |
| `order_count` | 订单数量（委托笔数） | Order Count (number of entrustments) |
| `order_count_all` | 所有订单数量（含撤单） | Total Order Count (including cancellations) |
| `cancel_count_all` | 撤单总笔数 | Total Cancellation Count |
| `deal_count` | 成交笔数 | Execution Count |
| `deal_amount` | 成交金额 | Execution Amount |
| `total_deal_amount_all` | 全部成交金额（总计） | Total Execution Amount (Overall) |
| `signal_deal_buy_amount` | 信号成交买入金额 | Signal Execution Buy Amount |
| `signal_deal_sell_amount` | 信号成交卖出金额 | Signal Execution Sell Amount |
| `oss_mega_amount_pct` | 超大单成交金额占比 | Mega Order Execution Amount Percentage |
| `oss_mega_count_pct` | 超大单成交笔数占比 | Mega Order Execution Count Percentage |
| `oss_large_amount_pct` | 大单成交金额占比 | Large Order Execution Amount Percentage |
| `oss_large_count_pct` | 大单成交笔数占比 | Large Order Execution Count Percentage |
| `oss_medium_amount_pct` | 中单成交金额占比 | Medium Order Execution Amount Percentage |
| `oss_medium_count_pct` | 中单成交笔数占比 | Medium Order Execution Count Percentage |
| `oss_small_amount_pct` | 小单成交金额占比 | Small Order Execution Amount Percentage |
| `oss_small_count_pct` | 小单成交笔数占比 | Small Order Execution Count Percentage |
| `oss_hot_money_count_pct` | 游资成交笔数占比 | Hot Money Execution Count Percentage |
| `oss_buy_amount_pct` | 主动买入金额占比（OSS分类） | Active Buy Amount Percentage (OSS Classification) |
| `oss_sell_amount_pct` | 主动卖出金额占比（OSS分类） | Active Sell Amount Percentage (OSS Classification) |
| `oss_mega_buy_pct` | 超大单中主动买入金额占比 | Active Buy Percentage within Mega Orders |
| `rs_interval_mean_ms` | 订单/成交间隔均值（毫秒） | Order/Execution Interval Mean (milliseconds) |
| `rs_interval_median_ms` | 订单/成交间隔中位数（毫秒） | Order/Execution Interval Median (milliseconds) |
| `rs_interval_cv` | 订单/成交间隔变异系数 | Order/Execution Interval Coefficient of Variation (CV) |
| `rs_burst_ratio` | 订单/成交爆发比率 | Order/Execution Burst Ratio |
| `rs_buy_interval_cv` | 买入订单间隔变异系数 | Buy Order Interval CV |
| `rs_sell_interval_cv` | 卖出订单间隔变异系数 | Sell Order Interval CV |
| `rs_split_similarity` | 订单拆分相似度 | Order Split Similarity |
| `rs_split_run_ratio` | 订单拆分连续运行比率 | Order Split Continuous Run Ratio |
| `cb_cancel_order_count` | 撤单笔数（特定行为统计） | Cancelled Order Count (Specific behavior stats) |
| `cb_cancel_order_ratio` | 撤单率（撤单笔数/总订单） | Cancellation Rate (Cancelled orders / Total orders) |
| `cb_cancel_volume_ratio` | 撤单量占比（撤单股数/总申报股数） | Cancelled Volume Percentage (Cancelled shares / Total declared shares) |
| `cb_cancel_amount_ratio` | 撤单金额占比（撤单金额/总申报金额） | Cancelled Amount Percentage (Cancelled amount / Total declared amount) |
| `cb_fast_cancel_ratio` | 快速撤单占比 | Fast Cancellation Percentage |
| `cb_cancel_interval_cv` | 撤单间隔时间变异系数 | Cancellation Time Interval CV |
| `cb_buy_cancel_ratio` | 买入委托撤单率 | Buy Entrustment Cancellation Rate |
| `cb_sell_cancel_ratio` | 卖出委托撤单率 | Sell Entrustment Cancellation Rate |
| `ap_active_buy_pct` | 主动买入成交额占比 | Active Buy Execution Amount Percentage |
| `ap_active_sell_pct` | 主动卖出成交额占比 | Active Sell Execution Amount Percentage |
| `ap_active_net_direction` | 主动买卖净方向（净主动买入/卖出） | Active Trading Net Direction (Net Active Buy/Sell) |
| `ap_unilateral_intensity` | 主动成交单边强度 | Active Execution Unilateral Intensity |
| `ap_dominant_direction` | 主动成交主导方向（买/卖/均衡） | Active Execution Dominant Direction (Buy / Sell / Balanced) |
| `ap_active_volume_pct` | 主动成交量占比 | Active Execution Volume Percentage |
| `ap_active_buy_run_max` | 最大连续主动买入成交笔数 | Maximum Continuous Active Buy Execution Count |
| `ap_active_sell_run_max` | 最大连续主动卖出成交笔数 | Maximum Continuous Active Sell Execution Count |
| `obp_at_best_bid_ratio` | 最优买价挂单占比 | Orders at Best Bid Price Ratio |
| `obp_near_best_bid_ratio` | 靠近最优买价挂单占比 | Orders Near Best Bid Price Ratio |
| `obp_cross_spread_buy` | 穿越价差买入挂单情况（或次数） | Cross-Spread Buy Order Occurrences (or Count) |
| `obp_avg_bid_offset` | 平均买单挂单价格偏移 | Average Buy Order Price Offset |
| `obp_at_best_ask_ratio` | 最优卖价挂单占比 | Orders at Best Ask Price Ratio |
| `obp_near_best_ask_ratio` | 靠近最优卖价挂单占比 | Orders Near Best Ask Price Ratio |
| `obp_cross_spread_sell` | 穿越价差卖出挂单情况 | Cross-Spread Sell Order Occurrences |
| `obp_avg_ask_offset` | 平均卖单挂单价格偏移 | Average Sell Order Price Offset |
| `pd_Q1_ratio` | 价格发现Q1比率（订单簿不平衡特征） | Price Discovery Q1 Ratio (Order book imbalance feature) |
| `pd_Q1_fast_ratio` | 价格发现Q1快速比率 | Price Discovery Q1 Fast Ratio |
| `pd_Q2_ratio` | 价格发现Q2比率 | Price Discovery Q2 Ratio |
| `pd_Q2_order_count` | 价格发现Q2订单数量 | Price Discovery Q2 Order Count |
| `pd_Q3_cv` | 价格发现Q3变异系数 | Price Discovery Q3 Coefficient of Variation |
| `pd_Q3_order_count` | 价格发现Q3订单数量 | Price Discovery Q3 Order Count |
| `pd_Q4_bid_ratio` | 价格发现Q4买方挂单比率 | Price Discovery Q4 Bid Ratio |
| `pd_Q4_ask_ratio` | 价格发现Q4卖方挂单比率 | Price Discovery Q4 Ask Ratio |
| `pd_Q5_deal_amount` | 价格发现Q5成交金额 | Price Discovery Q5 Execution Amount |
| `pd_Q5_impact` | 价格发现Q5冲击 | Price Discovery Q5 Impact |
| `pd_Q5_mean_price` | 价格发现Q5均价 | Price Discovery Q5 Mean Price |
| `pd_Q5_effective_threshold` | 价格发现Q5有效阈值 | Price Discovery Q5 Effective Threshold |
| `pd_Q5_large_threshold` | 价格发现Q5大单阈值 | Price Discovery Q5 Large Order Threshold |
| `pd_H1_buy_pct` | 价格发现H1买入成交占比 | Price Discovery H1 Buy Execution Percentage |
| `pd_H1_sell_pct` | 价格发现H1卖出成交占比 | Price Discovery H1 Sell Execution Percentage |
| `pd_H1_uni` | 价格发现H1独特性/单一性指标 | Price Discovery H1 Uniqueness/Singularity Index |
| `pd_H1_deal_amount` | 价格发现H1成交金额 | Price Discovery H1 Execution Amount |
| `pd_H1_mega_threshold` | 价格发现H1超大单阈值 | Price Discovery H1 Mega Order Threshold |
| `pd_H2_price_chg` | 价格发现H2价格变动 | Price Discovery H2 Price Change |
| `pd_H3_cross_buy` | 价格发现H3穿越价差买入情况 | Price Discovery H3 Cross-Spread Buy Instances |
| `pd_H3_cross_sell` | 价格发现H3穿越价差卖出情况 | Price Discovery H3 Cross-Spread Sell Instances |
| `pd_H3_deal_amount` | 价格发现H3成交金额 | Price Discovery H3 Execution Amount |
| `pd_H3_mega_threshold` | 价格发现H3超大单阈值 | Price Discovery H3 Mega Order Threshold |
| `pi_max_price_impact_pct` | 最大价格冲击百分比 | Maximum Price Impact Percentage |
| `pi_price_std_pct` | 价格标准差百分比（波动率） | Price Standard Deviation Percentage (Volatility) |
| `pi_vwap_deviation` | 成交均价与VWAP偏离度 | Execution Mean Price vs. VWAP Deviation |
| `pi_herfindahl_5min` | 5分钟成交集中度（赫芬达尔指数） | 5-Minute Execution Concentration (Herfindahl Index) |
| `pi_herfindahl_30min` | 30分钟成交集中度 | 30-Minute Execution Concentration |
| `pi_peak_amount_ratio` | 成交量峰值比率 | Trading Volume Peak Ratio |
| `pi_open_30min_amount_pct` | 开盘30分钟内成交额占比 | Trading Amount Percentage within 30 Mins of Open |
| `pi_close_10min_amount_pct` | 收盘前10分钟内成交额占比 | Trading Amount Percentage within 10 Mins of Close |
| `window_start_dt` | 窗口起始日期时间（精确） | Window Start Datetime (Exact) |
| `window_end_dt` | 窗口结束日期时间（精确） | Window End Datetime (Exact) |
