# API 接口文档

## 1. 接口名称：A股列表数据查询
**接口ID**: 1
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/all?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/all",
  "i_desc": "接口说明：查询所有A股股票数据，包括股票名称、股票代码，建议用户自己本地保留一分，每天请求一次即可",
  "req_rate": "请求频率：2次/天",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日收盘后30分钟更新"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "int",
    "example": "603176"
  },
  {
    "desc": "交易所",
    "name": "- jys",
    "type": "string",
    "example": "SH"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通灵股份"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "jys": "SH",
      "name": "N汇通",
      "api_code": "603176"
    },
    {
      "jys": "SZ",
      "name": "通灵股份",
      "api_code": "301168"
    }
  ]
}
```

---

## 2. 接口名称：股票/板块日,周，月K线行情
**接口ID**: 2
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/day?token=你的token&code=600004&endDate=2021-10-15&startDate=2021-10-10&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/day",
  "i_desc": "接口说明：可以查询所有A股股票历史日线，周线，月线行情，数据都是前复权的",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日16:00分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "股票/板块/概念K线;\n股票：600004;\n板块：BK0733",
    "name": "code",
    "type": "string",
    "default": "600004",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "交易开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2021-11-09",
    "required": "是"
  },
  {
    "desc": "交易截止时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2021-11-09",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "换手率",
    "name": "- turnoverRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "均价",
    "name": "- avgPrice",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌",
    "name": "- change",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "总股本",
    "name": "- totalShares",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌幅",
    "name": "- changeRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交量，单位(股)",
    "name": "- volume",
    "type": "Object",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "pb": [],
    "pe": [],
    "low": [],
    "pcf": [],
    "high": [],
    "open": [],
    "close": [],
    "amount": [],
    "change": [],
    "pe_ttm": [],
    "volume": [],
    "avgPrice": [],
    "preClose": [],
    "changeRatio": [],
    "totalShares": [],
    "totalCapital": [],
    "turnoverRatio": [],
    "transactionAmount": []
  }
}
```

---

## 3. 接口名称：龙虎榜查询
**接口ID**: 4
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/dragonTiger?token=你的token&date=2022-09-02`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/dragonTiger",
  "i_desc": "接口说明：龙虎榜查询",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2021-11-09",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "总成交量",
    "name": "- totalVolume",
    "type": "string",
    "example": ""
  },
  {
    "desc": "上榜原因",
    "name": "- reason",
    "type": "string",
    "example": ""
  },
  {
    "desc": "涨跌幅%",
    "name": "- chg",
    "type": "string",
    "example": ""
  },
  {
    "desc": "截至日期",
    "name": "- endDate",
    "type": "string",
    "example": ""
  },
  {
    "desc": "占总成交比列%",
    "name": "- sellAmountRatio",
    "type": "string",
    "example": ""
  },
  {
    "desc": "龙虎榜成交额（万元）",
    "name": "- topAmount",
    "type": "string",
    "example": ""
  },
  {
    "desc": "占总成交额比列%",
    "name": "- buyAmountRatio",
    "type": "string",
    "example": ""
  },
  {
    "desc": "总成交额（万元）",
    "name": "- totalAmount",
    "type": "string",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- thsCode",
    "type": "string",
    "example": ""
  },
  {
    "desc": "买入额（万元）",
    "name": "- buyAmount",
    "type": "string",
    "example": ""
  },
  {
    "desc": "卖出额(万元)",
    "name": "- sellAmount",
    "type": "string",
    "example": ""
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "string",
    "example": ""
  },
  {
    "desc": "换手率",
    "name": "- turnover",
    "type": "string",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "chg": [],
    "name": [],
    "close": [],
    "reason": [],
    "endDate": [],
    "thsCode": [],
    "turnover": [],
    "buyAmount": [],
    "topAmount": [],
    "sellAmount": [],
    "totalAmount": [],
    "totalVolume": [],
    "buyAmountRatio": [],
    "sellAmountRatio": []
  }
}
```

---

## 4. 接口名称：所有st股列表数据查询
**接口ID**: 5
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/st?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/st",
  "i_desc": "接口说明：所有st股列表数据查询",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15:30分更新"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": ""
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "300795.SZ",
      "name": "*ST米奥"
    }
  ]
}
```

---

## 5. 接口名称：查询当日是不是交易日
**接口ID**: 6
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/tradeDate?token=你的token&tradeDate=2021-10-20`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/tradeDate",
  "i_desc": "接口说明：交易日日历",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2021-11-09",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "是否为交易日：0:否，1:是",
    "name": "- isTradeDate",
    "type": "int",
    "example": "1"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "isTradeDate": 1
  }
}
```

---

## 6. 接口名称：分时成交量
**接口ID**: 7
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minList?token=你的token&code=600004&all=1`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minList",
  "i_desc": "接口说明：分时成交量，分析竞价爆量比较方便,，仅在9点15到15点有数据，金刚钻可用",
  "req_rate": "请求频率: 1次/一分钟",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 实时更新"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "返回全部数据，\n1-返回全部数据，\n0-返回最近一条",
    "name": "all",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "价格",
    "name": "- price",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "手数",
    "name": "- shoushu",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "单数",
    "name": "- danShu",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "涨跌标志：1-跌，2-涨,4-竞价阶段",
    "name": "- bsbz",
    "type": "int",
    "example": "1"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "bsbz": "4",
      "time": "09:16:00",
      "price": "29.55",
      "shoushu": "889"
    }
  ]
}
```

---

## 7. 接口名称：逐笔明细
**接口ID**: 8
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/secondList?token=你的token&code=600004&all=1`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/secondList",
  "i_desc": "接口说明：逐笔明细，分析竞价爆量比较方便，仅在9点15到15点有数据，金刚钻可用",
  "req_rate": "请求频率: 1次/3秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：实时更新"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "返回全部数据，\n1-返回全部数据，\n0-返回最近一条",
    "name": "all",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "价格",
    "name": "- price",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "手数",
    "name": "- shoushu",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "单数",
    "name": "- danShu",
    "type": "int",
    "example": "1"
  },
  {
    "desc": "涨跌标志：1-跌，2-涨,4-竞价阶段",
    "name": "- bsbz",
    "type": "int",
    "example": "1"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "bsbz": "4",
      "time": "09:16:00",
      "price": "29.55",
      "shoushu": "889"
    }
  ]
}
```

---

## 8. 接口名称：乖离率BIAS指标
**接口ID**: 11
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/bias2?token=你的token&code=600004&cycle1=6&cycle2=12&cycle3=24&startDate=2021-10-22&endDate=2021-10-22&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/bias2",
  "i_desc": "接口说明：日、周、月乖离率BIAS指标",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "周期3",
    "name": "cycle3",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "bias1值",
    "name": "- bias1",
    "type": "string",
    "example": "3.7532289925543"
  },
  {
    "desc": "bias2值",
    "name": "- bias2",
    "type": "string",
    "example": "5.6066816178177"
  },
  {
    "desc": "bias3值",
    "name": "- bias3",
    "type": "string",
    "example": "8.8734752451567"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "date": "2021-10-10",
      "bias1": "3.7532289925543",
      "bias2": "5.6066816178177",
      "bias3": "8.8734752451567",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 9. 接口名称：布林带boll数据查询
**接口ID**: 12
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/boll2?token=你的token&bandwidth=2&code=600004&cycle=26&startDate=2021-10-22&endDate=2021-10-22&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/boll2",
  "i_desc": "接口说明：日、周、月布林带boll数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "带宽",
    "name": "bandwidth",
    "type": "int",
    "default": "2",
    "example": "2",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "26",
    "example": "26",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "上轨",
    "name": "- UPPER",
    "type": "string",
    "example": "3.7532289925543"
  },
  {
    "desc": "下轨",
    "name": "- LOWER",
    "type": "string",
    "example": "5.6066816178177"
  },
  {
    "desc": "中轨",
    "name": "- MID",
    "type": "string",
    "example": "8.8734752451567"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "MID": "5.6066816178177",
      "date": "2021-10-10",
      "LOWER": "3.7532289925543",
      "UPPER": "8.8734752451567",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 10. 接口名称：日线cci数据查询
**接口ID**: 13
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/cci2?token=你的token&code=600004&cycle=14&startDate=2021-10-22&endDate=2021-10-22&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/cci2",
  "i_desc": "接口说明：日、周、月cci数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "26",
    "example": "26",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "上轨",
    "name": "- cci",
    "type": "string",
    "example": "3.7532289925543"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "cci": "8.8734752451567",
      "date": "2021-10-10",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 11. 接口名称：日线kdj数据查询
**接口ID**: 14
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/kdj2?token=你的token&calculationCycle=100&code=600004&cycle=9&cycle1=3&cycle2=3&startDate=2021-10-22&endDate=2021-10-22`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/kdj2",
  "i_desc": "接口说明：日、周、月kdj数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "9",
    "example": "9",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "3",
    "example": "3",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "3",
    "example": "3",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "k值",
    "name": "- k",
    "type": "string",
    "example": "74.026411185765"
  },
  {
    "desc": "d值",
    "name": "- d",
    "type": "string",
    "example": "74.026411185765"
  },
  {
    "desc": "j值",
    "name": "- j",
    "type": "string",
    "example": "75.970593695305"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "d": "75.970593695305",
      "j": "74.674472022278",
      "k": "74.026411185765",
      "date": "2021-10-10",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 12. 接口名称：5,10,20...日ma均线数据查询
**接口ID**: 15
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/ma2?token=你的token&code=600004&startDate=2021-10-22&endDate=2021-10-22&ma=5,10,20&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/ma2",
  "i_desc": "接口说明：日、周、月5,10,20...ma均线数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期,逗号分隔符必须为英文",
    "name": "ma",
    "type": "int",
    "default": "5,10,20",
    "example": "5,10,20...",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "ma5",
    "name": "- ma5",
    "type": "string",
    "example": "74"
  },
  {
    "desc": "ma10",
    "name": "- ma10",
    "type": "string",
    "example": "74"
  },
  {
    "desc": "ma20",
    "name": "- ma20",
    "type": "string",
    "example": "75.97"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "ma5": [
      11.426
    ],
    "date": [
      "2021-10-22"
    ],
    "ma10": [
      11.421
    ],
    "ma20": [
      11.023
    ],
    "api_code": "600004"
  }
}
```

---

## 13. 接口名称：日线macd数据查询
**接口ID**: 16
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/macd2?token=你的token&code=600004&cycle=9&startDate=2021-10-22&endDate=2021-10-22&longCycle=26&shortCycle=12&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/macd2",
  "i_desc": "接口说明：日、周、月线macd数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "9",
    "example": "9",
    "required": "是"
  },
  {
    "desc": "长期周期",
    "name": "longCycle",
    "type": "int",
    "default": "26",
    "example": "26",
    "required": "是"
  },
  {
    "desc": "短期周期",
    "name": "shortCycle",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "DEA值",
    "name": "- DEA",
    "type": "string",
    "example": "0.39808748104648"
  },
  {
    "desc": "DIFF值",
    "name": "- DIFF",
    "type": "string",
    "example": "0.46470061143322"
  },
  {
    "desc": "MACD值",
    "name": "- MACD",
    "type": "string",
    "example": "0.13322626077348"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "DEA": "74.026411185765",
      "DIFF": "75.970593695305",
      "MACD": "74.674472022278",
      "date": "2021-10-10",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 14. 接口名称：神奇九转指标
**接口ID**: 17
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/nineTurn?token=你的token&code=600004&date=2021-10-15&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/nineTurn",
  "i_desc": "接口说明：日、周、月神奇九转指标",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "低位九转：0:否，1:是",
    "name": "- lowNine",
    "type": "int",
    "example": "0"
  },
  {
    "desc": "高位九转：0:否，1:是",
    "name": "- highNine",
    "type": "int",
    "example": "1"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "date": "2021-10-10",
      "lowNine": 0,
      "api_code": "600004.SH",
      "highNine": 1
    }
  ]
}
```

---

## 15. 接口名称：日线wr数据查询
**接口ID**: 18
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/wr2?token=你的token&code=600004&cycle1=10&cycle2=6&startDate=2021-10-22&endDate=2021-10-22&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/wr2",
  "i_desc": "接口说明：日、周、月线wr数据查询",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "10",
    "example": "10",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "wr2值",
    "name": "- wr2",
    "type": "string",
    "example": "29.770992366412"
  },
  {
    "desc": "wr1值",
    "name": "- wr1",
    "type": "string",
    "example": "29.770992366412"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "wr1": 29.770992366412,
      "wr2": 29.770992366412,
      "date": "2021-10-10",
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 16. 接口名称：日线rsi指标
**接口ID**: 19
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/quota/rsi2?token=你的token&code=601088&cycle1=6&cycle2=12&cycle3=24&startDate=2021-10-22&endDate=2021-10-22&calculationCycle=100`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/quota/rsi2",
  "i_desc": "接口说明：日、周、月线RSI指标",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日收盘后30分钟更新"
}
```

### 请求参数
```json
[
  {
    "desc": "可传股票、板块、概念代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "周期3",
    "name": "cycle3",
    "type": "int",
    "default": "24",
    "example": "24",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "周期：100-日，101-周,102-月",
    "name": "calculationCycle",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2021-10-10"
  },
  {
    "desc": "rsi1值",
    "name": "- rsi1",
    "type": "string",
    "example": "29.770992366412"
  },
  {
    "desc": "rsi2值",
    "name": "- rsi2",
    "type": "string",
    "example": "29.770992366412"
  },
  {
    "desc": "rsi3值",
    "name": "- rsi3",
    "type": "string",
    "example": "29.770992366412"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "date": "2021-10-10",
      "rsi1": 29.770992366412,
      "rsi2": 29.770992366412,
      "rsi3": 29.770992366412,
      "api_code": "600004.SH"
    }
  ]
}
```

---

## 17. 接口名称：获取所有指数代码
**接口ID**: 20
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/ZSCode?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/ZSCode",
  "i_desc": "接口说明：获取所有指数代码",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "指数代码",
    "name": "- code",
    "type": "string",
    "example": "600004.SH"
  },
  {
    "desc": "指数名称",
    "name": "- name",
    "type": "string",
    "example": "2021-10-10"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "zs000001",
      "name": "上证指数"
    }
  ]
}
```

---

## 18. 接口名称：查询上证指数
**接口ID**: 21
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/index/sh?token=你的token&startDate=2021-10-20&endDate=2021-10-30`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/index/sh",
  "i_desc": "接口说明：查询上证指数",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "交易开始时间，格式：2021-10-20",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "交易结束时间，格式：2021-10-20",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "string",
    "example": "000001.SH"
  },
  {
    "desc": "交易日期",
    "name": "- time",
    "type": "Object[]",
    "example": "2021-10-10"
  },
  {
    "desc": "成交量",
    "name": "- volume",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "均价",
    "name": "- avgPrice",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌",
    "name": "- change",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌幅",
    "name": "- changeRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "time": "Object[242]",
    "table": {
      "low": "Object[242]",
      "high": "Object[242]",
      "open": "Object[242]",
      "close": "Object[242]",
      "amount": "Object[242]",
      "change": "Object[242]",
      "volume": "Object[242]",
      "avgPrice": "Object[242]",
      "changeRatio": "Object[242]"
    },
    "thscode": "",
    "api_code": "000001.SH"
  }
}
```

---

## 19. 接口名称：查询创业板指
**接口ID**: 22
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/index/cyb?token=你的token&startDate=2021-10-20&endDate=2021-10-30`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/index/cyb",
  "i_desc": "接口说明：查询创业板指",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "交易开始时间，格式：2021-10-20",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "交易结束时间，格式：2021-10-20",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "string",
    "example": "000001.SH"
  },
  {
    "desc": "交易日期",
    "name": "- time",
    "type": "Object[]",
    "example": "2021-10-10"
  },
  {
    "desc": "成交量",
    "name": "- volume",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "均价",
    "name": "- avgPrice",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌",
    "name": "- change",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌幅",
    "name": "- changeRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "time": "Object[242]",
    "table": {
      "low": "Object[242]",
      "high": "Object[242]",
      "open": "Object[242]",
      "close": "Object[242]",
      "amount": "Object[242]",
      "change": "Object[242]",
      "volume": "Object[242]",
      "avgPrice": "Object[242]",
      "changeRatio": "Object[242]"
    },
    "thscode": "",
    "api_code": "000001.SH"
  }
}
```

---

## 20. 接口名称：查询深圳成指
**接口ID**: 23
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/index/sz?token=你的token&startDate=2021-10-20&endDate=2021-10-30`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/index/sz",
  "i_desc": "接口说明：查询深圳成指",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15:30分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "交易开始时间，格式：2021-10-20",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "交易结束时间，格式：2021-10-20",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "string",
    "example": "000001.SH"
  },
  {
    "desc": "交易日期",
    "name": "- time",
    "type": "Object[]",
    "example": "2021-10-10"
  },
  {
    "desc": "成交量",
    "name": "- volume",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "均价",
    "name": "- avgPrice",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌",
    "name": "- change",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌幅",
    "name": "- changeRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "time": "Object[242]",
    "table": {
      "low": "Object[242]",
      "high": "Object[242]",
      "open": "Object[242]",
      "close": "Object[242]",
      "amount": "Object[242]",
      "change": "Object[242]",
      "volume": "Object[242]",
      "avgPrice": "Object[242]",
      "changeRatio": "Object[242]"
    },
    "thscode": "",
    "api_code": "000001.SH"
  }
}
```

---

## 21. 接口名称：所有ETF代码
**接口ID**: 28
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/fund/etf?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/fund/etf",
  "i_desc": "接口说明：所有ETF代码",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "159707"
  },
  {
    "desc": "ETF名称",
    "name": "- name",
    "type": "string",
    "example": "地产ETF"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "159707",
      "name": "地产ETF"
    }
  ]
}
```

---

## 22. 接口名称：查询基金列表
**接口ID**: 29
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/fund/all?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/fund/all",
  "i_desc": "接口说明：查询基金列表",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "支持基金代码和名称模糊查询(非必填)",
    "name": "keyWords",
    "type": "string",
    "default": "",
    "example": "159713",
    "required": "否"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000031"
  },
  {
    "desc": "基金类型",
    "name": "- type",
    "type": "string",
    "example": "混合型-偏股"
  },
  {
    "desc": "基金名称",
    "name": "- name",
    "type": "string",
    "example": "华夏复兴混合"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "000031",
      "name": "华夏复兴混合",
      "type": "混合型-偏股"
    }
  ]
}
```

---

## 23. 接口名称：涨停股池
**接口ID**: 30
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/ZTPool?token=你的token&date=2022-09-16`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/ZTPool",
  "i_desc": "接口说明：涨停股池",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间，格式：2022-09-16",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2022-09-16",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000419"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通程控股"
  },
  {
    "desc": "涨跌幅%",
    "name": "- changeRatio",
    "type": "string",
    "example": "10.01"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "5.91"
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "string",
    "example": "142304401"
  },
  {
    "desc": "流通市值",
    "name": "- flowCapital",
    "type": "string",
    "example": "3210902084"
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "string",
    "example": "3212573497"
  },
  {
    "desc": "换手率%",
    "name": "- turnoverRatio",
    "type": "string",
    "example": "4.610971"
  },
  {
    "desc": "封板资金",
    "name": "- ceilingAmount",
    "type": "string",
    "example": "102224679"
  },
  {
    "desc": "首次封板时间",
    "name": "- firstCeilingTime",
    "type": "string",
    "example": "134027"
  },
  {
    "desc": "最后封板时间",
    "name": "- lastCeilingTime",
    "type": "string",
    "example": "134027"
  },
  {
    "desc": "炸板次数",
    "name": "- bombNum",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "连扳数量",
    "name": "- lbNum",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "所属行业",
    "name": "- industry",
    "type": "string",
    "example": "商业百货"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2022-09-16"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  },
  {
    "desc": "股票涨停原因",
    "name": "- stock_reason",
    "type": "string",
    "example": ""
  },
  {
    "desc": "主题上涨原因",
    "name": "- plate_reason",
    "type": "string",
    "example": ""
  },
  {
    "desc": "涨停主题",
    "name": "- plate_name",
    "type": "string",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "000419",
      "name": "通程控股",
      "time": "2022-09-16",
      "lbNum": 1,
      "amount": 142304401,
      "bombNum": 0,
      "industry": "商业百货",
      "lastPrice": 5.91,
      "changeRatio": 10.055866,
      "flowCapital": 3210902084,
      "totalCapital": 3212573497,
      "ceilingAmount": 102224679,
      "turnoverRatio": 4.610971,
      "lastCeilingTime": "134027",
      "firstCeilingTime": "134027"
    }
  ]
}
```

---

## 24. 接口名称：强势股池
**接口ID**: 31
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/QSPool?token=你的token&date=2022-09-16`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/QSPool",
  "i_desc": "接口说明：强势股池",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间，格式：2022-09-16",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2022-09-16",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000419"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通程控股"
  },
  {
    "desc": "涨跌幅%",
    "name": "- changeRatio",
    "type": "string",
    "example": "10.01"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "5.91"
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "string",
    "example": "142304401"
  },
  {
    "desc": "流通市值",
    "name": "- flowCapital",
    "type": "string",
    "example": "3210902084"
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "string",
    "example": "3212573497"
  },
  {
    "desc": "换手率%",
    "name": "- turnoverRatio",
    "type": "string",
    "example": "4.610971"
  },
  {
    "desc": "涨停统计",
    "name": "- zttj",
    "type": "string",
    "example": "{'days':3,'ct':2}1"
  },
  {
    "desc": "涨速",
    "name": "- zs",
    "type": "string",
    "example": "0.0"
  },
  {
    "desc": "是否新高，0-否，1-是",
    "name": "- nh",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "量比",
    "name": "- lb",
    "type": "string",
    "example": "1.2846934795379639"
  },
  {
    "desc": "所属行业",
    "name": "- industry",
    "type": "string",
    "example": "商业百货"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2022-09-16"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "nh": 1,
      "zs": "0.0",
      "code": "000419",
      "name": "通程控股",
      "time": "2022-09-16",
      "zttj": "{'days':0,'ct':0}",
      "amount": 142304401,
      "industry": "商业百货",
      "lastPrice": 5.91,
      "changeRatio": 10.055866,
      "flowCapital": 3210902084,
      "totalCapital": 3212573497,
      "turnoverRatio": 4.610971
    }
  ]
}
```

---

## 25. 接口名称：次新股池
**接口ID**: 32
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/CXPool?token=你的token&date=2022-09-08`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/CXPool",
  "i_desc": "接口说明：次新股池",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间，格式：2022-09-16",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2022-09-16",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000419"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通程控股"
  },
  {
    "desc": "涨跌幅%",
    "name": "- changeRatio",
    "type": "string",
    "example": "10.01"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "5.91"
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "string",
    "example": "142304401"
  },
  {
    "desc": "流通市值",
    "name": "- flowCapital",
    "type": "string",
    "example": "3210902084"
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "string",
    "example": "3212573497"
  },
  {
    "desc": "换手率%",
    "name": "- turnoverRatio",
    "type": "string",
    "example": "4.610971"
  },
  {
    "desc": "涨停统计",
    "name": "- zttj",
    "type": "string",
    "example": {
      "ct": 2,
      "days": 3
    }
  },
  {
    "desc": "上市日期",
    "name": "- ipod",
    "type": "string",
    "example": "20211019"
  },
  {
    "desc": "开板几日",
    "name": "- ods",
    "type": "string",
    "example": "226"
  },
  {
    "desc": "是否新高，0-否，1-是",
    "name": "- nh",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "开板日期",
    "name": "- od",
    "type": "string",
    "example": "20211019"
  },
  {
    "desc": "所属行业",
    "name": "- industry",
    "type": "string",
    "example": "商业百货"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2022-09-16"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "nh": 1,
      "od": "20211019",
      "ods": 226,
      "code": "000419",
      "ipod": "20211019",
      "name": "通程控股",
      "time": "2022-09-16",
      "zttj": {
        "ct": 0,
        "days": 0
      },
      "amount": 142304401,
      "industry": "商业百货",
      "lastPrice": 5.91,
      "changeRatio": 10.055866,
      "flowCapital": 3210902084,
      "totalCapital": 3212573497,
      "turnoverRatio": 4.610971
    }
  ]
}
```

---

## 26. 接口名称：炸板股池
**接口ID**: 33
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/ZBPool?token=你的token&date=2022-09-16`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/ZBPool",
  "i_desc": "接口说明：炸板股池",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间，格式：2022-09-16",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2022-09-16",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000419"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通程控股"
  },
  {
    "desc": "涨跌幅%",
    "name": "- changeRatio",
    "type": "string",
    "example": "10.01"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "5.91"
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "string",
    "example": "142304401"
  },
  {
    "desc": "流通市值",
    "name": "- flowCapital",
    "type": "string",
    "example": "3210902084"
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "string",
    "example": "3212573497"
  },
  {
    "desc": "换手率%",
    "name": "- turnoverRatio",
    "type": "string",
    "example": "4.610971"
  },
  {
    "desc": "封板资金",
    "name": "- ceilingAmount",
    "type": "string",
    "example": "102224679"
  },
  {
    "desc": "首次封板时间",
    "name": "- firstCeilingTime",
    "type": "string",
    "example": "134027"
  },
  {
    "desc": "炸板次数",
    "name": "- bombNum",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "涨停统计",
    "name": "- zttj",
    "type": "string",
    "example": {
      "ct": 2,
      "days": 3
    }
  },
  {
    "desc": "上市日期",
    "name": "- ipod",
    "type": "string",
    "example": "20211019"
  },
  {
    "desc": "涨速%",
    "name": "- zs",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "是否新高，0-否，1-是",
    "name": "- nh",
    "type": "string",
    "example": "0"
  },
  {
    "desc": "所属行业",
    "name": "- industry",
    "type": "string",
    "example": "商业百货"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2022-09-16"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "zs": -0.1,
      "code": "000419",
      "ipod": "20211019",
      "name": "通程控股",
      "time": "2022-09-16",
      "zttj": {
        "ct": 0,
        "days": 0
      },
      "amount": 142304401,
      "industry": "商业百货",
      "lastPrice": 5.91,
      "changeRatio": 10.055866,
      "flowCapital": 3210902084,
      "totalCapital": 3212573497,
      "turnoverRatio": 4.610971
    }
  ]
}
```

---

## 27. 接口名称：跌停股池
**接口ID**: 34
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/DTPool?token=你的token&date=2022-09-16`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/DTPool",
  "i_desc": "接口说明：跌停股池",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15点30"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间，格式：2022-09-16",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2022-09-16",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "000419"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "通程控股"
  },
  {
    "desc": "涨跌幅%",
    "name": "- changeRatio",
    "type": "string",
    "example": "10.01"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "5.91"
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "string",
    "example": "142304401"
  },
  {
    "desc": "流通市值",
    "name": "- flowCapital",
    "type": "string",
    "example": "3210902084"
  },
  {
    "desc": "总市值",
    "name": "- totalCapital",
    "type": "string",
    "example": "3212573497"
  },
  {
    "desc": "换手率%",
    "name": "- turnoverRatio",
    "type": "string",
    "example": "4.610971"
  },
  {
    "desc": "封板资金",
    "name": "- ceilingAmount",
    "type": "string",
    "example": "102224679"
  },
  {
    "desc": "首次封板时间",
    "name": "- firstCeilingTime",
    "type": "string",
    "example": "134027"
  },
  {
    "desc": "最后封板时间",
    "name": "- lastCeilingTime",
    "type": "string",
    "example": "134027"
  },
  {
    "desc": "动态市盈率",
    "name": "- pe",
    "type": "string",
    "example": "27"
  },
  {
    "desc": "板上成交额",
    "name": "- fba",
    "type": "string",
    "example": "33023498"
  },
  {
    "desc": "连续跌停天数",
    "name": "- days",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "开板次数",
    "name": "- oc",
    "type": "string",
    "example": "2"
  },
  {
    "desc": "所属行业",
    "name": "- industry",
    "type": "string",
    "example": "商业百货"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2022-09-16"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "光伏设备,江苏版块"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "oc": 2,
      "pe": 27,
      "fba": 33023498,
      "code": "000419",
      "days": 1,
      "name": "通程控股",
      "time": "2022-09-16",
      "amount": 142304401,
      "industry": "商业百货",
      "lastPrice": 5.91,
      "changeRatio": 10.055866,
      "flowCapital": 3210902084,
      "totalCapital": 3212573497,
      "turnoverRatio": 4.610971
    }
  ]
}
```

---

## 28. 接口名称：全量异动数据历史
**接口ID**: 35
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/change/allHistory?token=你的token&endDate=2023-03-22&startDate=2023-03-21&type=8201`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/change/allHistory",
  "i_desc": "接口说明：全量异动数据历史",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午4点30分"
}
```

### 请求参数
```json
[
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  },
  {
    "desc": "异动类型",
    "name": "type",
    "type": "string",
    "default": "8201",
    "example": "8201:火箭发射,\n8202:快速反弹,\n8207:竞价上涨,\n8209:高开5日线,\n8211:向上缺口,\n8215:60日大幅上涨,\n8204:加速下跌,\n8203:高台跳水,\n8208:竞价下跌,\n8210:低开5日线,\n8212:向下缺口,\n8216:60日大幅下跌,\n8193:大笔买入,\n8194:大笔卖出,\n64:有大买盘,\n128:有大卖盘,\n4:封涨停板,\n32:打开跌停板,\n8213:60日新高,\n8:封跌停板,\n16:打开涨停板,\n8214:60日新低",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "异动时间",
    "name": "- time",
    "type": "string",
    "example": "145553"
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "873152"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "string",
    "example": "天宏锂电"
  },
  {
    "desc": "异动类型",
    "name": "- type",
    "type": "string",
    "example": "8201"
  },
  {
    "desc": "异动信息",
    "name": "- info",
    "type": "string",
    "example": "26.13%"
  },
  {
    "desc": "异动名称",
    "name": "- typeName",
    "type": "string",
    "example": "火箭发射"
  },
  {
    "desc": "日期",
    "name": "- dateId",
    "type": "string",
    "example": "2023-03-21"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "000419",
      "info": "26.13%",
      "name": "通程控股",
      "time": 145553,
      "type": 8201,
      "dateId": "2023-03-21",
      "typeName": "火箭发射"
    }
  ]
}
```

---

## 29. 接口名称：股票异动数据历史
**接口ID**: 36
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/change/codeHistory?token=你的token&endDate=2023-12-22&startDate=2023-12-21&code=300688`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/change/codeHistory",
  "i_desc": "接口说明：股票异动数据历史",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午4点30分"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "300688",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-03-24",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "异动时间",
    "name": "- time",
    "type": "string",
    "example": "145553"
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "873152"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "string",
    "example": "天宏锂电"
  },
  {
    "desc": "异动类型",
    "name": "- type",
    "type": "string",
    "example": "8201"
  },
  {
    "desc": "异动信息",
    "name": "- info",
    "type": "string",
    "example": "26.13%"
  },
  {
    "desc": "异动名称",
    "name": "- typeName",
    "type": "string",
    "example": "火箭发射"
  },
  {
    "desc": "日期",
    "name": "- dateId",
    "type": "string",
    "example": "2023-03-21"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "000419",
      "info": "26.13%",
      "name": "通程控股",
      "time": 145553,
      "type": 8201,
      "dateId": "2023-03-21",
      "typeName": "火箭发射"
    }
  ]
}
```

---

## 30. 接口名称：获取游资名称
**接口ID**: 37
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/youzi/name?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/youzi/name",
  "i_desc": "接口说明：获取游资名称",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午5点40"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "游资名称",
    "name": "- youziName",
    "type": "string",
    "example": "章盟主"
  },
  {
    "desc": "操盘风格",
    "name": "- cpfg",
    "type": "string",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "cpfg": "说到中国最早的游资，只有两个人有这个资格，一个就是“敢死队总舵主”徐翔，另一个就是我们今天说的被称为游资“盟主”的章建平，章盟主是“60后”的老大，短线手法非常犀利，更厉害的是据说他没有任何助手，所有东西都是自己一个人做。",
      "youziName": "章盟主"
    }
  ]
}
```

---

## 31. 接口名称：全量游资上榜交割单历史
**接口ID**: 38
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/youzi/all?token=你的token&date=2023-03-24`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/youzi/all",
  "i_desc": "接口说明：全量游资上榜交割单历史",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午5点40"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "游资名称",
    "name": "- yzmc",
    "type": "string",
    "example": "92科比"
  },
  {
    "desc": "营业部",
    "name": "- yyb",
    "type": "string",
    "example": "兴业证券股份有限公司南京天元东路证券营业部"
  },
  {
    "desc": "单日榜或三日榜",
    "name": "- sblx",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "股票代码",
    "name": "- gpdm",
    "type": "string",
    "example": "001337"
  },
  {
    "desc": "股票名称",
    "name": "- gpmc",
    "type": "string",
    "example": "四川黄金"
  },
  {
    "desc": "买入金额",
    "name": "- mrje",
    "type": "string",
    "example": "14470401"
  },
  {
    "desc": "卖出金额",
    "name": "- mcje",
    "type": "string",
    "example": "15080"
  },
  {
    "desc": "净流入金额",
    "name": "- jlrje",
    "type": "string",
    "example": "14455321"
  },
  {
    "desc": "2023-03-22",
    "name": "- rq",
    "type": "string",
    "example": "日期"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "gl": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股",
      "rq": "2023-03-22",
      "yyb": "兴业证券股份有限公司南京天元东路证券营业部",
      "gpdm": "001337",
      "gpmc": "四川黄金",
      "mcje": "15080",
      "mrje": "14470401",
      "yzmc": "92科比",
      "jlrje": "14455321"
    }
  ]
}
```

---

## 32. 接口名称：单个游资上榜交割单历史
**接口ID**: 39
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/youzi/jgdhis?token=你的token&yzmc=92科比&date=2023-03-24`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/youzi/jgdhis",
  "i_desc": "接口说明：单个游资上榜交割单历史",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午5点40"
}
```

### 请求参数
```json
[
  {
    "desc": "游资名称",
    "name": "yzmc",
    "type": "string",
    "default": "",
    "example": "上塘路",
    "required": "是"
  },
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "游资名称",
    "name": "- yzmc",
    "type": "string",
    "example": "92科比"
  },
  {
    "desc": "营业部",
    "name": "- yyb",
    "type": "string",
    "example": "兴业证券股份有限公司南京天元东路证券营业部"
  },
  {
    "desc": "单日榜或三日榜",
    "name": "- sblx",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "股票代码",
    "name": "- gpdm",
    "type": "string",
    "example": "001337"
  },
  {
    "desc": "股票名称",
    "name": "- gpmc",
    "type": "string",
    "example": "四川黄金"
  },
  {
    "desc": "买入金额",
    "name": "- mrje",
    "type": "string",
    "example": "14470401"
  },
  {
    "desc": "卖出金额",
    "name": "- mcje",
    "type": "string",
    "example": "15080"
  },
  {
    "desc": "净流入金额",
    "name": "- jlrje",
    "type": "string",
    "example": "14455321"
  },
  {
    "desc": "2023-03-22",
    "name": "- rq",
    "type": "string",
    "example": "日期"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "gl": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股",
      "rq": "2023-03-22",
      "yyb": "兴业证券股份有限公司南京天元东路证券营业部",
      "gpdm": "001337",
      "gpmc": "四川黄金",
      "mcje": "15080",
      "mrje": "14470401",
      "yzmc": "92科比",
      "jlrje": "14455321"
    }
  ]
}
```

---

## 33. 接口名称：个股游资上榜交割单
**接口ID**: 40
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/youzi/gegu?token=你的token&code=001337&endDate=2023-03-24&startDate=2023-03-21`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/youzi/gegu",
  "i_desc": "接口说明：个股游资上榜交割单",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午5点40"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "001337",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-03-21",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-03-24",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "游资名称",
    "name": "- yzmc",
    "type": "string",
    "example": "92科比"
  },
  {
    "desc": "营业部",
    "name": "- yyb",
    "type": "string",
    "example": "兴业证券股份有限公司南京天元东路证券营业部"
  },
  {
    "desc": "单日榜或三日榜",
    "name": "- sblx",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "股票代码",
    "name": "- gpdm",
    "type": "string",
    "example": "001337"
  },
  {
    "desc": "股票名称",
    "name": "- gpmc",
    "type": "string",
    "example": "四川黄金"
  },
  {
    "desc": "买入金额",
    "name": "- mrje",
    "type": "string",
    "example": "14470401"
  },
  {
    "desc": "卖出金额",
    "name": "- mcje",
    "type": "string",
    "example": "15080"
  },
  {
    "desc": "净流入金额",
    "name": "- jlrje",
    "type": "string",
    "example": "14455321"
  },
  {
    "desc": "2023-03-22",
    "name": "- rq",
    "type": "string",
    "example": "日期"
  },
  {
    "desc": "概念",
    "name": "- gl",
    "type": "string",
    "example": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "gl": "贵金属,四川板块,昨日连板_含一字,昨日涨停_含一字,黄金概念,次新股",
      "rq": "2023-03-22",
      "yyb": "兴业证券股份有限公司南京天元东路证券营业部",
      "gpdm": "001337",
      "gpmc": "四川黄金",
      "mcje": "15080",
      "mrje": "14470401",
      "yzmc": "92科比",
      "jlrje": "14455321"
    }
  ]
}
```

---

## 34. 接口名称：股票人气排行榜
**接口ID**: 41
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/change/renQi?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/change/renQi",
  "i_desc": "接口说明：股票人气排名",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：每隔30分钟一次"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "人气值",
    "name": "- rate",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "002261"
  },
  {
    "desc": "涨幅",
    "name": "- rise_and_fall",
    "type": "string",
    "example": "9.98"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "string",
    "example": "拓维信息"
  },
  {
    "desc": "原因分析",
    "name": "- analyse",
    "type": "string",
    "example": "行业原因：\nAI算力需求快速增长推动高速光模块需求量提升。天风证券指出，AI算力的指数级增长正在倒逼光模块技术加速迭代。"
  },
  {
    "desc": "标记：板块概念，几天几板",
    "name": "- tag",
    "type": "string",
    "example": {
      "concept_tag": [
        "共封装光学(CPO)",
        "光纤概念"
      ],
      "popularity_tag": "3天2板"
    }
  },
  {
    "desc": "排序",
    "name": "- order",
    "type": "string",
    "example": "1"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "zf": 9.9885,
      "tag": {
        "concept_tag": [
          "共封装光学(CPO)",
          "光纤概念"
        ],
        "popularity_tag": "3天2板"
      },
      "code": "600105",
      "name": "永鼎股份",
      "rate": "215841.0",
      "order": 1,
      "analyse": "行业原因：\nAI算力需求快速增长推动高速光模块需求量提升。天风证券指出，AI算力的指数级增长正在倒逼光模块技术加速迭代。Scale-up场景正向CPO演进，2026年或将成为CPO商用元年。\n公司原因：\n1、据2026年2月26日机构调研，公司贯通“光棒—光纤—光缆—芯片—器件—模块”光通信全产业链，100G EML及硅光100mW/70mW CW HP芯片已配套800G/1.6T光模块，受益于全球AI算力需求。\n2、据2025年12月16日投资者关系活动记录表，公司HF1200系列REBCO超导带材实现单根1435米批量化制备，4mm带材20K/20T条件下临界电流达435A，已用于可控核聚变磁体并与中科院、核工业西南物理研究院等客户合作。\n3、据2026年1月28日业绩预增公告，预计2025年度归母净利润2.00亿元至3.00亿元，同比增长225.66%至388.48%。\n\n（免责声明：本内容由AI技术搜集公开信息总结生成，仅供参考，不构成投资建议，以上市公司公告为准）"
    }
  ]
}
```

---

## 35. 接口名称：次日涨停价/新股涨停价
**接口ID**: 43
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/chrome/limitUp?flag=2&close=10.01&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/chrome/limitUp",
  "i_desc": "接口说明：计算次日/新股上市涨停价",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：任意时间都可调用"
}
```

### 请求参数
```json
[
  {
    "desc": "1-涨停5%，2-涨停10%，3-涨停44%，4-涨停20%",
    "name": "flag",
    "type": "string",
    "default": "",
    "example": "2",
    "required": "是"
  },
  {
    "desc": "昨日收盘价",
    "name": "close",
    "type": "string",
    "default": "",
    "example": "10.01",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "涨停价",
    "name": "data",
    "type": "string",
    "example": "11.01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": "2.32"
}
```

---

## 36. 接口名称：早盘热点板块竞价
**接口ID**: 44
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/bkjj?endDate=2023-09-01&startDate=2023-09-01&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/bkjj",
  "i_desc": "接口说明：早盘热点板块or极速下跌板块竞价，方便提前发现资金今日的方向",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点26分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-09-01",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-09-01",
    "required": "是"
  },
  {
    "desc": "0-看空，1-看多",
    "name": "type",
    "type": "string",
    "default": "",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "880482"
  },
  {
    "desc": "板块名称",
    "name": "- bkName",
    "type": "string",
    "example": "房地产"
  },
  {
    "desc": "看多or看空力度，数值越大越好",
    "name": "- ld",
    "type": "string",
    "example": "97.9798"
  },
  {
    "desc": "竞价涨幅",
    "name": "- jjzf",
    "type": "string",
    "example": "1.5307"
  },
  {
    "desc": "上涨家数",
    "name": "- szjs",
    "type": "string",
    "example": "29"
  },
  {
    "desc": "下跌家数",
    "name": "- xdjs",
    "type": "string",
    "example": "72"
  },
  {
    "desc": "1-看多，0-看空",
    "name": "- type",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "ld": "97.9798",
      "date": "2023-09-01",
      "jjzf": "1.5307",
      "szjs": 29,
      "type": 1,
      "xdjs": 72,
      "bkCode": "880482",
      "bkName": "房地产"
    }
  ]
}
```

---

## 37. 接口名称：早盘热点板块竞价所属个股
**接口ID**: 45
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/bkCodeList?endDate=2023-09-01&startDate=2023-09-01&bkCode=880431&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/bkCodeList",
  "i_desc": "接口说明：早盘热点板块竞价所属个股，有助于将挖掘涨停潜力个股",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点26分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-09-01",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-09-01",
    "required": "是"
  },
  {
    "desc": "热点板块代码",
    "name": "bkCode",
    "type": "string",
    "default": "",
    "example": "880431",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "880482"
  },
  {
    "desc": "板块名称",
    "name": "- bkName",
    "type": "string",
    "example": "房地产"
  },
  {
    "desc": "1：看多，0看空",
    "name": "- type",
    "type": "string",
    "example": "97.9798"
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "600685"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "中船防务"
  },
  {
    "desc": "竞价涨幅",
    "name": "- jjzf",
    "type": "string",
    "example": "0.2925"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  },
  {
    "desc": "上一个交易日连板数",
    "name": "- preLbNum",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "上一个交易日几天几板",
    "name": "- preZttj",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "上一个涨停交易日",
    "name": "- preDate",
    "type": "string",
    "example": "2023-08-31"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "300589",
      "date": "2023-09-01",
      "jjzf": "-0.2926",
      "name": "江龙船艇",
      "type": 0,
      "bkCode": "880431",
      "bkName": "船舶",
      "preDate": "",
      "preZttj": "",
      "preLbNum": "0"
    }
  ]
}
```

---

## 38. 接口名称：早盘竞价涨停委托单
**接口ID**: 46
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjztwtd?date=2023-09-01&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjztwtd",
  "i_desc": "接口说明：竞价涨停委托单",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点26分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2023-09-01",
    "required": "是"
  },
  {
    "desc": "1-主板，2-创业板",
    "name": "type",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "603326"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "我乐家居"
  },
  {
    "desc": "竞价涨幅",
    "name": "- jjzf",
    "type": "string",
    "example": "9.98094"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  },
  {
    "desc": "委买额",
    "name": "- wme",
    "type": "string",
    "example": "160046915"
  },
  {
    "desc": "净额",
    "name": "- je",
    "type": "string",
    "example": "4481242"
  },
  {
    "desc": "竞价成交额",
    "name": "- jjcje",
    "type": "string",
    "example": "7613153"
  },
  {
    "desc": "竞价换手率",
    "name": "- jjhs",
    "type": "string",
    "example": "0.55"
  },
  {
    "desc": "流通股",
    "name": "- ltg",
    "type": "string",
    "example": "1379547351"
  },
  {
    "desc": "主力",
    "name": "- zl",
    "type": "string",
    "example": "游资"
  },
  {
    "desc": "连板",
    "name": "- lb",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "板块",
    "name": "- bk",
    "type": "string",
    "example": "装修家具、地产链"
  },
  {
    "desc": "连板",
    "name": "- lb",
    "type": "string",
    "example": "5连板"
  },
  {
    "desc": "1-主板，2-创业板",
    "name": "- type",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "竞价日期",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "bk": "装修家具、地产链",
      "je": "4481242",
      "lb": "5连板",
      "zl": "游资",
      "ltg": "1379547351",
      "wme": "160046915",
      "code": "603326",
      "date": "2023-09-01",
      "jjZf": "9.98094",
      "jjhs": "0.55",
      "name": "我乐家居",
      "type": 1,
      "jjcje": "7613153"
    }
  ]
}
```

---

## 39. 接口名称：个股资金流向
**接口ID**: 47
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/codeFlowHistory?code=600004&startDate=2026-07-31&endDate=2026-07-31&pageNo=1&pageSize=100&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/codeFlowHistory",
  "i_desc": "接口说明：股票历史资金流，黄金套餐可用",
  "req_rate": "请求限制：10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日16：30"
}
```

### 请求参数
```json
[
  {
    "desc": "代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  },
  {
    "desc": "页码",
    "name": "pageNo",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "每页行数",
    "name": "pageSize",
    "type": "string",
    "default": "50",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "白云机场"
  },
  {
    "desc": "涨跌幅",
    "name": "- pxChangeRate",
    "type": "string",
    "example": "-1.38"
  },
  {
    "desc": "最新价",
    "name": "- lastPx",
    "type": "string",
    "example": "10.73"
  },
  {
    "desc": "特大单净流入",
    "name": "- superNetTurnover",
    "type": "string",
    "example": "-1.5245291E7"
  },
  {
    "desc": "大单净流入",
    "name": "- largeNetTurnover",
    "type": "string",
    "example": "-17.6"
  },
  {
    "desc": "中单净流入",
    "name": "- mediumNetTurnover",
    "type": "string",
    "example": "-8549201.0"
  },
  {
    "desc": "小单净流入",
    "name": "- littleNetTurnover",
    "type": "string",
    "example": "-9.87"
  },
  {
    "desc": "主力净流入",
    "name": "- mainNetTurnover",
    "type": "string",
    "example": "-6696090.0"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "pages": 1,
    "total": 1,
    "current": 1,
    "records": [
      {
        "code": "002384",
        "mark": "HSA",
        "name": "东山精密",
        "time": "2026-08-01",
        "lastPx": 171.48,
        "market": "sz",
        "pxChangeRate": 0.0598,
        "mainNetTurnover": 3246310817,
        "largeNetTurnover": -656144900,
        "superNetTurnover": 3902455717,
        "littleNetTurnover": -1296385380,
        "mediumNetTurnover": -1949925438
      }
    ]
  }
}
```

---

## 40. 接口名称：Level2历史数据
**接口ID**: 48
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址: 无",
  "i_desc": "接口说明：Levle2数据保存在百度网盘，请加微信联系，需要单独购买，数据包含：十档委托，逐笔成交，逐笔委托。数据量极大，约4000G",
  "req_rate": "请求限制：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日15：30"
}
```

### 请求参数
```json
[
  {
    "desc": "代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2023-10-16",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2023-10-17",
    "required": "是"
  },
  {
    "desc": "页码",
    "name": "pageNo",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "每页行数",
    "name": "pageSize",
    "type": "string",
    "default": "50",
    "example": "50",
    "required": "是"
  }
]
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

## 41. 接口名称：增强版热点板块竞价
**接口ID**: 49
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/bkjjzq?tradeDate=2023-11-08&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/bkjjzq",
  "i_desc": "接口说明：早盘热点板块or极速下跌板块竞价，方便提前发现资金今日的方向",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点26分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2023-11-08",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "880482"
  },
  {
    "desc": "板块名称",
    "name": "- bkName",
    "type": "string",
    "example": "房地产"
  },
  {
    "desc": "竞价涨幅",
    "name": "- jjzf",
    "type": "string",
    "example": "1.5307"
  },
  {
    "desc": "上涨家数",
    "name": "- szjs",
    "type": "string",
    "example": "29"
  },
  {
    "desc": "下跌家数",
    "name": "- xdjs",
    "type": "string",
    "example": "72"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "date": "2023-09-01",
      "jjzf": "1.5307",
      "szjs": 29,
      "xdjs": 72,
      "bkCode": "880482",
      "bkName": "房地产"
    }
  ]
}
```

---

## 42. 接口名称：增强版热点板块竞价所属个股
**接口ID**: 50
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/zqbkCodeList?tradeDate=2023-11-17&bkCode=37112745&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/zqbkCodeList",
  "i_desc": "接口说明：早盘热点板块竞价所属个股，有助于将挖掘涨停潜力个股",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点26分更新"
}
```

### 请求参数
```json
[
  {
    "desc": "开始时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2023-11-03",
    "required": "是"
  },
  {
    "desc": "热点板块代码",
    "name": "bkCode",
    "type": "string",
    "default": "",
    "example": "880431",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "880482"
  },
  {
    "desc": "板块名称",
    "name": "- bkName",
    "type": "string",
    "example": "房地产"
  },
  {
    "desc": "1：看多，0看空",
    "name": "- type",
    "type": "string",
    "example": "97.9798"
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "string",
    "example": "600685"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "中船防务"
  },
  {
    "desc": "竞价涨幅",
    "name": "- jjzf",
    "type": "string",
    "example": "0.2925"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "string",
    "example": "2023-09-01"
  },
  {
    "desc": "上一个交易日连板数",
    "name": "- preLbNum",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "上一个交易日几天几板",
    "name": "- preZttj",
    "type": "string",
    "example": "1"
  },
  {
    "desc": "上一个涨停交易日",
    "name": "- preDate",
    "type": "string",
    "example": "2023-08-31"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "300589",
      "date": "2023-09-01",
      "jjzf": "-0.2926",
      "name": "江龙船艇",
      "type": 0,
      "bkCode": "880431",
      "bkName": "船舶",
      "preDate": "",
      "preZttj": "",
      "preLbNum": "0"
    }
  ]
}
```

---

## 43. 接口名称：实时五档委托单
**接口ID**: 51
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/wudang?code=600004&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/wudang",
  "i_desc": "接口说明：实时获取买卖五档数据，仅在9点25至15点有数据，金刚钻可用",
  "req_rate": "请求频率: 10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：实时更新"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "string",
    "example": "白云机场"
  },
  {
    "desc": "当前价",
    "name": "- current",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "总成交",
    "name": "- totalV",
    "type": "string",
    "example": "2000000"
  },
  {
    "desc": "内盘",
    "name": "- insideV",
    "type": "string",
    "example": "2000000"
  },
  {
    "desc": "外盘",
    "name": "- outerV",
    "type": "string",
    "example": "2000000"
  },
  {
    "desc": "买1价",
    "name": "- buy1",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "买1量",
    "name": "- buyV1",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "买1金额",
    "name": "- buyAmt1",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "买2价",
    "name": "- buy2",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "买2量",
    "name": "- buyV2",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "买2金额",
    "name": "- buyAmt2",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "买3价",
    "name": "- buy3",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "买3量",
    "name": "- buyV3",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "买3金额",
    "name": "- buyAmt3",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "买4价",
    "name": "- buy4",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "买4量",
    "name": "- buyV4",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "买4金额",
    "name": "- buyAmt4",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "买5价",
    "name": "- buy5",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "买5量",
    "name": "- buyV5",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "买5金额",
    "name": "- buyAmt5",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "卖1价",
    "name": "- sell1",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "卖1量",
    "name": "- sellV1",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "卖1金额",
    "name": "- sellAmt1",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "卖2价",
    "name": "- sell2",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "卖2量",
    "name": "- sellV2",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "卖2金额",
    "name": "- sellAmt2",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "卖3价",
    "name": "- sell3",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "卖3量",
    "name": "- sellV3",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "卖3金额",
    "name": "- sellAmt3",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "卖4价",
    "name": "- sell4",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "卖4量",
    "name": "- sellV4",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "卖4金额",
    "name": "- sellAmt4",
    "type": "string",
    "example": "20003333"
  },
  {
    "desc": "卖5价",
    "name": "- sell5",
    "type": "string",
    "example": "10.27"
  },
  {
    "desc": "卖5量",
    "name": "- sellV5",
    "type": "string",
    "example": "20003"
  },
  {
    "desc": "卖5金额",
    "name": "- sellAmt5",
    "type": "string",
    "example": "20003333"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "buy1": "10.27",
    "buy2": "10.26",
    "buy3": "10.25",
    "buy4": "10.24",
    "buy5": "10.23",
    "code": "600004",
    "name": "白云机场",
    "buyV1": "3142",
    "buyV2": "1917",
    "buyV3": "1479",
    "buyV4": "587",
    "buyV5": "348",
    "sell1": "10.28",
    "sell2": "10.29",
    "sell3": "10.30",
    "sell4": "10.31",
    "sell5": "10.32",
    "outerV": "211106",
    "sellV1": "719",
    "sellV2": "13",
    "sellV3": "324",
    "sellV4": "366",
    "sellV5": "261",
    "totalV": "332404",
    "buyAmt1": "3226834",
    "buyAmt2": "1966842",
    "buyAmt3": "1515975",
    "buyAmt4": "601088",
    "buyAmt5": "356004",
    "current": "10.28",
    "insideV": "121298",
    "sellAmt1": "739132",
    "sellAmt2": "13377",
    "sellAmt3": "333720",
    "sellAmt4": "377346",
    "sellAmt5": "269352"
  }
}
```

---

## 44. 接口名称：查询沪深300
**接口ID**: 52
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/index/sh300?token=你的token&startDate=2021-10-20&endDate=2021-10-30`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/index/sh300",
  "i_desc": "接口说明：查询沪深300",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日收盘后30分钟更新"
}
```

### 请求参数
```json
[
  {
    "desc": "交易开始时间，格式：2021-10-20",
    "name": "startDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  },
  {
    "desc": "交易结束时间，格式：2021-10-20",
    "name": "endDate",
    "type": "string",
    "default": "2021-10-22",
    "example": "2021-10-22",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "string",
    "example": "000001.SH"
  },
  {
    "desc": "交易日期",
    "name": "- time",
    "type": "Object[]",
    "example": "2021-10-10"
  },
  {
    "desc": "成交量",
    "name": "- volume",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "均价",
    "name": "- avgPrice",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌",
    "name": "- change",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "涨跌幅",
    "name": "- changeRatio",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "time": "Object[242]",
    "table": {
      "low": "Object[242]",
      "high": "Object[242]",
      "open": "Object[242]",
      "close": "Object[242]",
      "amount": "Object[242]",
      "change": "Object[242]",
      "volume": "Object[242]",
      "avgPrice": "Object[242]",
      "changeRatio": "Object[242]"
    },
    "thscode": "",
    "api_code": "000001.SH"
  }
}
```

---

## 45. 接口名称：收益回测接口
**接口ID**: 53
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/huice?strategyId=99999999&codes=600004&price=10.0&buyDate=2024-03-27&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/huice",
  "i_desc": "接口说明：可以回测买入股票后次日竞价开盘收益，次日收盘收益，次日涨停价收益（若涨停则按涨停价计算，若无涨停则按照收盘价计算）,白银以上可用",
  "req_rate": "请求频率: 40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：随时"
}
```

### 请求参数
```json
[
  {
    "desc": "策略id，在策略回测下面先创建您的策略，将生成的策略id传入此处接口",
    "name": "strategyId",
    "type": "string",
    "default": "",
    "example": "99999999",
    "required": "是"
  },
  {
    "desc": "买入时间，格式：2024-03-25",
    "name": "buyDate",
    "type": "string",
    "default": "2024-03-25",
    "example": "2024-03-25",
    "required": "是"
  },
  {
    "desc": "股票代码集合,至少传一只票，多只票必须用英文逗号拼接，格式：600004,000901",
    "name": "codes",
    "type": "string",
    "default": "600006",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "买入价格",
    "name": "price",
    "type": "string",
    "default": "",
    "example": "10",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- api_code",
    "type": "string",
    "example": "000001.SH"
  },
  {
    "desc": "交易日期",
    "name": "- time",
    "type": "Object[]",
    "example": "2021-10-10"
  },
  {
    "desc": "买入后第一个交易日开盘收益涨幅",
    "name": "- t1Open",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "买入后第一个交易日收盘收益涨幅",
    "name": "- t1Close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "买入后第一个交易日如果盘中触及涨停价时的收益涨幅，如果盘中未触及涨停，以收盘收益涨幅为准",
    "name": "- t1Ht",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "msg": "success",
    "code": 20000,
    "data": {
      "code": "600004",
      "name": "白云机场",
      "t1Ht": "0.7",
      "t2Ht": "0.8",
      "time": "2024-03-27",
      "t1Open": "-1.1"
    }
  }
}
```

---

## 46. 接口名称：个股竞价异动数据
**接口ID**: 54
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/jjCode?tradeDate=2024-04-03&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/jjCode",
  "i_desc": "接口说明：个股竞价异动",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午9点27"
}
```

### 请求参数
```json
[
  {
    "desc": "交易时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2024-04-03",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "301209"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "Object[]",
    "example": "联合化学"
  },
  {
    "desc": "9点25涨幅",
    "name": "- pct25",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "9点25竞价金额",
    "name": "- amt25",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "昨日连板",
    "name": "- lb",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "流通市值",
    "name": "- ltsz",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "强度",
    "name": "- upScore",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "竞价异动类型:\n竞价抢筹\n破板异动\n一进二接力\n竞价异动",
    "name": "- jjType",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "lb": 0,
      "code": "301209",
      "ltsz": 5.4,
      "name": "联合化学",
      "time": "2024-04-03",
      "amt25": 345.82,
      "pct25": -2.27,
      "jjType": "破板异动",
      "upScore": 0
    }
  ]
}
```

---

## 47. 接口名称：一分钟K线实时数据
**接口ID**: 55
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minkLine?code=000001&all=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minkLine",
  "i_desc": "接口说明：查询每分钟实时K线数据。仅在9点30到15点有数据，金刚钻可用",
  "req_rate": "请求频率：1次/一分钟",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 实时更新"
}
```

### 请求参数
```json
[
  {
    "desc": "传股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "返回全部数据，\n1-返回全部数据，\n0-返回最近一条",
    "name": "all",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "成交量",
    "name": "- volume",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "Object[]",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "low": "3069.30",
      "high": "3069.53",
      "open": "3069.50",
      "time": "2024-04-03 15:00:00",
      "close": "3069.30",
      "amount": "4791384832.00",
      "volume": "4748635"
    }
  ]
}
```

---

## 48. 接口名称：AI智能选股
**接口ID**: 56
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/xuangu?strategy=创业板，今日涨停，换手率大于10，竞价涨幅大于1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/xuangu",
  "i_desc": "接口说明：AI智能选股，使用自然语言，白话文的形式选股，随时选出你想要的好股，本接口特殊，不能直接调用，需要本地安装我们提供的一个软件和运行我们提供的代码才行，请咨询技术",
  "req_rate": "请求频率：10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 实时更新"
}
```

### 请求参数
```json
[
  {
    "desc": "策略详情，比如：创业板，今日涨停，换手率大于10",
    "name": "strategy",
    "type": "string",
    "default": "",
    "example": "创业板，今日涨停，换手率大于10",
    "required": "是"
  }
]
```

### 返回参数说明
```json
无
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "300486",
      "最新价": "5.93",
      "market_code": "33",
      "上市板块": "创业板",
      "注册地址": "山西省太原市尖草坪区中北高新技术产业开发区丰源路59号",
      "经营范围": "物流设备、自动化生产线、输送线、仓储设备、涂装设备、自动监控系统、自动化配送中心、立体停车库、电气设备、工业机器人的设计、制造、安装、调试；自有房屋经营租赁；电力业务：太阳能光伏发电；电力供应：售电业务；机电设备安装工程；进出口：自营和代理各类商品和技术的进出口（但国家限定公司经营或禁止进出口的商品和技术除外）。（依法须经批准的项目，经相关部门批准后方可开展经营活动）。",
      "股票代码": "300486.SZ",
      "股票简称": "东杰智能",
      "最新涨跌幅": "20.041",
      "涨停[20240704]": "涨停",
      "几天几板[20240704]": "首板涨停",
      "涨停类型[20240704]": "放量涨停",
      "涨停封单量[20240704]": "423225.0",
      "涨停封单额[20240704]": "2509724.25",
      "最终涨停时间[20240704]": " 14:53:02",
      "涨停原因类别[20240704]": "曾向国电高科支付预付款+智能物流+机器人+国企",
      "涨停开板次数[20240704]": "3",
      "涨停明细数据[20240704]": "[{\"code\":\"300486.SZ\",\"time\":1720056811552,\"openTime\":1720058177117,\"duration\":1365565,\"updatedTime\":1720058177117,\"firstVol\":7.39147E7,\"highestVol\":9.7456075E7,\"firstVolDivLTGB\":0.18670637910502347,\"firstVolDivVol\":5.464993217806095,\"highestVolDivLTGB\":0.24617120660758415,\"highestVolDivVol\":6.129873063242823},{\"code\":\"300486.SZ\",\"time\":1720058267118,\"openTime\":1720058282118,\"duration\":15000,\"updatedTime\":1720058282118,\"firstVol\":374900.0,\"highestVol\":374900.0,\"firstVolDivLTGB\":9.469864793670717E-4,\"firstVolDivVol\":0.009097983805249078,\"highestVolDivLTGB\":9.469864793670717E-4,\"highestVolDivVol\":0.009097983805249078},{\"code\":\"300486.SZ\",\"time\":1720075892245,\"openTime\":1720075967245,\"duration\":75000,\"updatedTime\":1720075967245,\"firstVol\":9162725.0,\"highestVol\":9162725.0,\"firstVolDivLTGB\":0.023144776444808356,\"firstVolDivVol\":0.10518119907984638,\"highestVolDivLTGB\":0.023144776444808356,\"highestVolDivVol\":0.10518119907984638},{\"code\":\"300486.SZ\",\"time\":1720075982245,\"openTime\":null,\"duration\":417755,\"updatedTime\":1720076400000,\"firstVol\":75500.0,\"highestVol\":2494575.0,\"firstVolDivLTGB\":1.907108007260974E-4,\"firstVolDivVol\":8.561368113428262E-4,\"highestVolDivLTGB\":0.006301223784388138,\"highestVolDivVol\":0.028151291063805248}]",
      "连续涨停天数[20240704]": 1,
      "首次涨停时间[20240704]": " 09:33:31",
      "a股市值(不含限售股)[20240704]": "2347612200.000",
      "涨停封单量占成交量比[20240704]": 0.4721479560921645,
      "涨停封单量占流通a股比[20240704]": 0.10690540216861266
    }
  ]
}
```

---

## 49. 接口名称：情绪周期
**接口ID**: 57
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/emotionalCycle?token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/emotionalCycle",
  "i_desc": "接口说明：情绪周期折线图，包括最近40日涨跌停家数，大面情绪，大肉情绪，上涨家数，打板成功率，上涨比列，短线选手复盘必备工具",
  "req_rate": "请求频率：10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日17：00"
}
```

### 请求参数
```json
[]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "图例名称",
    "name": "- colNameList",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "图例对应数据",
    "name": "- contentList",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- date1",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "上涨比列",
    "name": "- szbl",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "连板家数",
    "name": "- lbjs",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "压力高度",
    "name": "- ylgd",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "最新高度",
    "name": "- zxgd",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "大面情绪",
    "name": "- dmqx",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "大肉情绪",
    "name": "- drqx",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "涨停家数",
    "name": "- ztjs",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "打板成功率",
    "name": "- dbcgl",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "跌停家数",
    "name": "- dtjs",
    "type": "Object",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "colNameList": [
      "date1",
      "szbl",
      "lbjs",
      "ylgd",
      "zxgd",
      "dmqx",
      "drqx",
      "ztjs",
      "dbcgl",
      "dtjs"
    ],
    "contentList": [
      [
        20241008,
        94.1706,
        357,
        "13",
        13,
        0,
        319,
        770,
        98.094,
        0
      ],
      [
        20241009,
        5.5108,
        31,
        "14",
        14,
        291,
        44,
        44,
        60,
        789
      ],
      [
        20241010,
        56.1551,
        7,
        "14",
        8,
        48,
        71,
        72,
        64.6341,
        37
      ],
      [
        20241011,
        8.2443,
        7,
        "8",
        3,
        15,
        31,
        36,
        39.2157,
        32
      ],
      [
        20241014,
        94.0052,
        9,
        "8",
        4,
        1,
        106,
        110,
        75.2066,
        2
      ],
      [
        20241015,
        15.0028,
        21,
        "4",
        3,
        2,
        42,
        56,
        43.0556,
        2
      ],
      [
        20241016,
        51.0109,
        20,
        "4",
        4,
        2,
        80,
        94,
        40.566,
        4
      ],
      [
        20241017,
        33.5641,
        19,
        "5",
        5,
        7,
        38,
        58,
        76.1194,
        5
      ],
      [
        20241018,
        95.247,
        27,
        "6",
        6,
        0,
        136,
        132,
        58.6957,
        0
      ],
      [
        20241021,
        70.4903,
        54,
        "7",
        7,
        3,
        153,
        174,
        82.1053,
        0
      ],
      [
        20241022,
        67.2843,
        43,
        "8",
        8,
        22,
        86,
        116,
        56.0606,
        0
      ],
      [
        20241023,
        51.4419,
        35,
        "9",
        9,
        2,
        85,
        104,
        52.7559,
        2
      ],
      [
        20241024,
        39.985,
        28,
        "10",
        10,
        4,
        88,
        100,
        44.3609,
        3
      ],
      [
        20241025,
        80.4568,
        43,
        "11",
        11,
        1,
        114,
        169,
        65.9686,
        0
      ],
      [
        20241028,
        79.0223,
        87,
        "12",
        12,
        0,
        134,
        247,
        72.1088,
        1
      ],
      [
        20241029,
        19.7753,
        56,
        "12",
        9,
        2,
        79,
        131,
        76.3158,
        3
      ],
      [
        20241030,
        43.3683,
        57,
        "12",
        10,
        5,
        118,
        157,
        40.7216,
        4
      ],
      [
        20241031,
        65.7491,
        71,
        "12",
        11,
        1,
        121,
        192,
        71.6981,
        2
      ],
      [
        20241101,
        18.2584,
        39,
        "12",
        12,
        137,
        65,
        104,
        58.0645,
        139
      ],
      [
        20241104,
        84.0292,
        29,
        "13",
        13,
        6,
        124,
        153,
        54.3011,
        36
      ],
      [
        20241105,
        94.7043,
        48,
        "14",
        14,
        0,
        158,
        185,
        52.7523,
        0
      ],
      [
        20241106,
        52.797,
        56,
        "14",
        10,
        5,
        103,
        151,
        64.6409,
        3
      ],
      [
        20241107,
        84.6586,
        49,
        "14",
        11,
        2,
        184,
        199,
        37.7682,
        7
      ],
      [
        20241108,
        41.4999,
        41,
        "11",
        7,
        6,
        78,
        122,
        69.0323,
        3
      ],
      [
        20241111,
        73.6803,
        40,
        "7",
        5,
        5,
        127,
        158,
        45.5399,
        15
      ],
      [
        20241112,
        27.7185,
        23,
        "7",
        6,
        11,
        49,
        84,
        56.25,
        15
      ],
      [
        20241113,
        48.0255,
        11,
        "7",
        7,
        4,
        60,
        70,
        41.3793,
        7
      ],
      [
        20241114,
        9.113,
        13,
        "8",
        8,
        10,
        23,
        35,
        43.1034,
        19
      ],
      [
        20241115,
        17.3515,
        14,
        "9",
        9,
        18,
        61,
        73,
        43.2099,
        23
      ],
      [
        20241118,
        21.7716,
        27,
        "10",
        10,
        59,
        43,
        86,
        82.2222,
        55
      ],
      [
        20241119,
        84.3482,
        17,
        "11",
        11,
        4,
        91,
        97,
        58.2524,
        12
      ],
      [
        20241120,
        85.3303,
        39,
        "12",
        12,
        1,
        119,
        158,
        48.3146,
        2
      ],
      [
        20241121,
        47.8537,
        45,
        "13",
        13,
        4,
        75,
        112,
        55.2,
        3
      ],
      [
        20241122,
        8.0037,
        37,
        "13",
        10,
        3,
        46,
        74,
        69.2308,
        6
      ],
      [
        20241125,
        69.6772,
        47,
        "13",
        11,
        8,
        122,
        157,
        69.4118,
        15
      ],
      [
        20241126,
        28.6567,
        31,
        "11",
        7,
        27,
        60,
        92,
        52.8302,
        55
      ],
      [
        20241127,
        80.78,
        21,
        "11",
        8,
        4,
        99,
        103,
        37.963,
        15
      ],
      [
        20241128,
        47.2279,
        32,
        "11",
        9,
        6,
        61,
        95,
        61.9469,
        6
      ],
      [
        20241129,
        79.9925,
        34,
        "11",
        10,
        2,
        107,
        134,
        55.5556,
        7
      ],
      [
        20241202,
        86.6256,
        54,
        "11",
        11,
        1,
        98,
        169,
        68.1081,
        5
      ]
    ]
  }
}
```

---

## 50. 接口名称：下单买卖
**接口ID**: 58
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn",
  "i_desc": "需要开户，提供ptrade/miniQMT行情交易接口，能实现自动下单买卖，提供机构同款极速交易柜台和机构VIP打板通道，详情V联系"
}
```

### 请求参数
```json
无
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

## 51. 接口名称：早盘抢筹委托金额排序
**接口ID**: 59
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=0&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：早盘抢筹委托金额排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "0",
    "example": "0",
    "required": "是"
  },
  {
    "desc": "按照抢筹委托金额排序",
    "name": "type",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照开盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 52. 接口名称：早盘抢筹成交金额排序
**接口ID**: 60
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=0&type=2&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：早盘抢筹成交金额排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "0",
    "example": "0",
    "required": "是"
  },
  {
    "desc": "早盘抢筹成交金额排序",
    "name": "type",
    "type": "string",
    "default": "2",
    "example": "2",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照开盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 53. 接口名称：早盘抢筹开盘金额排序
**接口ID**: 61
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=0&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：早盘抢筹开盘金额排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "0",
    "example": "0",
    "required": "是"
  },
  {
    "desc": "早盘抢筹开盘金额排序",
    "name": "type",
    "type": "string",
    "default": "3",
    "example": "3",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照开盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 54. 接口名称：早盘抢筹涨幅排序
**接口ID**: 62
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=0&type=4&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：早盘抢筹涨幅排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "0",
    "example": "0",
    "required": "是"
  },
  {
    "desc": "早盘抢筹涨幅排序",
    "name": "type",
    "type": "string",
    "default": "4",
    "example": "4",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照开盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 55. 接口名称：尾盘抢筹委托金额排序
**接口ID**: 63
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=1&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：尾盘抢筹委托金额排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15：10"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "尾盘抢筹委托金额排序",
    "name": "type",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照收盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 56. 接口名称：尾盘抢筹成交金额排序
**接口ID**: 64
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=1&type=2&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：尾盘抢筹成交金额排序。黄金100w可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15：10"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "尾盘抢筹成交金额排序",
    "name": "type",
    "type": "string",
    "default": "2",
    "example": "2",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照收盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 57. 接口名称：尾盘抢筹收盘金额排序
**接口ID**: 65
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=1&type=3&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：尾盘抢筹收盘金额排序，黄金100w可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15：10"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "尾盘抢筹成交金额排序",
    "name": "type",
    "type": "string",
    "default": "3",
    "example": "3",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照收盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 58. 接口名称：尾盘抢筹涨幅排序
**接口ID**: 66
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/jjqc?tradeDate=2025-03-04&period=1&type=4&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/jjqc",
  "i_desc": "接口说明：尾盘抢筹涨幅排序，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日15：10"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-04",
    "required": "是"
  },
  {
    "desc": "抢筹类型，0-竞价抢筹，1-尾盘抢筹",
    "name": "period",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "尾盘抢筹成交金额排序",
    "name": "type",
    "type": "string",
    "default": "4",
    "example": "4",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "开盘金额",
    "name": "- openAmt",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "抢筹涨幅",
    "name": "- qczf",
    "type": "Double",
    "example": ""
  },
  {
    "desc": "抢筹成交额",
    "name": "- qccje",
    "type": "String",
    "example": ""
  },
  {
    "desc": "抢筹委托金额",
    "name": "- qcwtje",
    "type": "Long",
    "example": ""
  },
  {
    "desc": "排序类型：1-按照抢筹委托金额排序，2-按照抢筹成交金额排序，3-按照收盘金额顺序排序，4-按照抢筹涨幅排序",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "抢筹类型，0-早盘竞价抢筹，1-尾盘抢筹",
    "name": "- period",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "002725",
      "name": "跃岭股份",
      "qczf": 9.98,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5730304,
      "period": 0,
      "qcwtje": 729434002,
      "openAmt": 5730304
    },
    {
      "code": "002227",
      "name": "奥 特 迅",
      "qczf": 10.02,
      "time": "2025-03-04",
      "type": 1,
      "qccje": 5296440,
      "period": 0,
      "qcwtje": 5296440,
      "openAmt": 45699975
    }
  ]
}
```

---

## 59. 接口名称：严重异动提醒
**接口ID**: 67
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/alarmData?tradeDate=2025-03-04&type=4&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/alarmData",
  "i_desc": "接口说明：严重异动提醒，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-13",
    "required": "是"
  },
  {
    "desc": "严重异动提醒",
    "name": "type",
    "type": "string",
    "default": "4",
    "example": "4",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "异动详情",
    "name": "- content",
    "type": "String",
    "example": ""
  },
  {
    "desc": "1-股东减持，2-大比列解禁，3-风险监控，4-严重异动提醒",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "688213",
      "name": "思特威",
      "time": "2025-03-13",
      "type": 1,
      "content": "国家集成电路基金二期等股东拟合计减持不超2.99%公司股份"
    },
    {
      "code": "301085",
      "name": "亚康股份",
      "time": "2025-03-13",
      "type": 1,
      "content": "多名股东拟合计减持不超3.81%公司股份"
    }
  ]
}
```

---

## 60. 接口名称：风险监控
**接口ID**: 68
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/alarmData?tradeDate=2025-03-04&type=3&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/alarmData",
  "i_desc": "接口说明：风险监控，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-13",
    "required": "是"
  },
  {
    "desc": "风险监控",
    "name": "type",
    "type": "string",
    "default": "3",
    "example": "3",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "异动详情",
    "name": "- content",
    "type": "String",
    "example": ""
  },
  {
    "desc": "1-股东减持，2-大比列解禁，3-风险监控，4-严重异动提醒",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "688213",
      "name": "思特威",
      "time": "2025-03-13",
      "type": 1,
      "content": "国家集成电路基金二期等股东拟合计减持不超2.99%公司股份"
    },
    {
      "code": "301085",
      "name": "亚康股份",
      "time": "2025-03-13",
      "type": 1,
      "content": "多名股东拟合计减持不超3.81%公司股份"
    }
  ]
}
```

---

## 61. 接口名称：大比列解禁
**接口ID**: 69
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/alarmData?tradeDate=2025-03-04&type=2&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/alarmData",
  "i_desc": "接口说明：大比列解禁，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-13",
    "required": "是"
  },
  {
    "desc": "大比列解禁",
    "name": "type",
    "type": "string",
    "default": "2",
    "example": "2",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "异动详情",
    "name": "- content",
    "type": "String",
    "example": ""
  },
  {
    "desc": "1-股东减持，2-大比列解禁，3-风险监控，4-严重异动提醒",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "688213",
      "name": "思特威",
      "time": "2025-03-13",
      "type": 1,
      "content": "国家集成电路基金二期等股东拟合计减持不超2.99%公司股份"
    },
    {
      "code": "301085",
      "name": "亚康股份",
      "time": "2025-03-13",
      "type": 1,
      "content": "多名股东拟合计减持不超3.81%公司股份"
    }
  ]
}
```

---

## 62. 接口名称：大股东减持
**接口ID**: 70
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/alarmData?tradeDate=2025-03-04&type=1&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/alarmData",
  "i_desc": "接口说明：大股东减持，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：26"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-03-13",
    "required": "是"
  },
  {
    "desc": "大股东减持",
    "name": "type",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "异动详情",
    "name": "- content",
    "type": "String",
    "example": ""
  },
  {
    "desc": "1-股东减持，2-大比列解禁，3-风险监控，4-严重异动提醒",
    "name": "- type",
    "type": "int",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "688213",
      "name": "思特威",
      "time": "2025-03-13",
      "type": 1,
      "content": "国家集成电路基金二期等股东拟合计减持不超2.99%公司股份"
    },
    {
      "code": "301085",
      "name": "亚康股份",
      "time": "2025-03-13",
      "type": 1,
      "content": "多名股东拟合计减持不超3.81%公司股份"
    }
  ]
}
```

---

## 63. 接口名称：竞价一字板
**接口ID**: 71
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/jjyizi/list?tradeDate=2025-08-22&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/jjyizi/list",
  "i_desc": "接口说明：竞价一字板，黄金可用",
  "req_rate": "请求频率：40次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 交易日9：27"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2025-08-22",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "跌停数量",
    "name": "- dtCount",
    "type": "int",
    "example": ""
  },
  {
    "desc": "涨停一板数量",
    "name": "- zt1Count",
    "type": "int",
    "example": ""
  },
  {
    "desc": "涨停二板以上数量",
    "name": "- zt2Count",
    "type": "String",
    "example": ""
  },
  {
    "desc": "涨停列表",
    "name": "- todayList",
    "type": "int",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "-- code",
    "type": "String",
    "example": ""
  },
  {
    "desc": "今日封单额",
    "name": "-- fde",
    "type": "String",
    "example": ""
  },
  {
    "desc": "增减单额，，昨日竞价一字板才有这个值，是于昨日比较的增减单额",
    "name": "-- fdeDiff",
    "type": "String",
    "example": ""
  },
  {
    "desc": "价格",
    "name": "-- jjPrice",
    "type": "String",
    "example": ""
  },
  {
    "desc": "连板",
    "name": "-- lb",
    "type": "String",
    "example": ""
  },
  {
    "desc": "流通市值",
    "name": "-- ltsz",
    "type": "String",
    "example": ""
  },
  {
    "desc": "股票名称",
    "name": "-- name",
    "type": "String",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "-- time",
    "type": "String",
    "example": ""
  },
  {
    "desc": "ztyy",
    "name": "-- 涨停板块",
    "type": "String",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "dtCount": 0,
    "zt1Count": 3,
    "zt2Count": 3,
    "todayList": [
      {
        "id": 885,
        "lb": 1,
        "fde": 1126816644,
        "code": "300192",
        "ltsz": 6976502548,
        "name": "科德教育",
        "time": "2025-08-22",
        "type": 1,
        "ztyy": "东数西算/算力",
        "fdeDiff": 1126816644,
        "jjPrice": "21.590000"
      }
    ]
  }
}
```

---

## 64. 接口名称：k线实时5/15/30分钟数据
**接口ID**: 72
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/kline?code=600004&type=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/kline",
  "i_desc": "接口说明：可以查询所有A股股票5分钟K线，15分钟K线，30分钟K线，60分钟K线，120分钟K线，数据都是前复权的，金刚钻可用",
  "req_rate": "请求频率：1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间: 在K线间隔周期内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码：如：600004;",
    "name": "code",
    "type": "string",
    "default": "600004",
    "example": "600004",
    "required": "是"
  },
  {
    "desc": "周期：5分钟，15分钟，30分钟，60分钟，120分钟",
    "name": "type",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "成交额",
    "name": "- amount",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "最高价",
    "name": "- high",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "最低价",
    "name": "- low",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "收盘价",
    "name": "- close",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "开盘价",
    "name": "- open",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "成交量，单位(股)",
    "name": "- volume",
    "type": "Object",
    "example": ""
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "Object",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "low": "9.890",
      "code": "600004",
      "high": "9.910",
      "open": "9.910",
      "time": "2025-11-04 10:40:00",
      "close": "9.900",
      "amount": "2185391.9739",
      "volume": "220800"
    }
  ]
}
```

---

## 65. 接口名称：macd实时数据
**接口ID**: 73
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minMacd?code=600004&cycle=9&longCycle=26&shortCycle=12&interval=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minMacd",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，60分钟，120分钟macd数据，金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：间隔周期内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "9",
    "example": "9",
    "required": "是"
  },
  {
    "desc": "长期周期",
    "name": "longCycle",
    "type": "int",
    "default": "26",
    "example": "26",
    "required": "是"
  },
  {
    "desc": "短期周期",
    "name": "shortCycle",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "时间间隔:5分钟;15分钟;30分钟，60分钟，120分钟",
    "name": "interval",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "obejct[]",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "dea",
    "name": "- dea",
    "type": "obejct[]",
    "example": "0.39"
  },
  {
    "desc": "dif值",
    "name": "- dif",
    "type": "string",
    "example": "0.46"
  },
  {
    "desc": "macd值",
    "name": "- macd",
    "type": "obejct[]",
    "example": "0.138"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "dea": [
      0.01
    ],
    "dif": [
      0.01
    ],
    "date": [
      "2025-11-04 11:00:00"
    ],
    "macd": [
      0.01
    ],
    "api_code": "600004"
  }
}
```

---

## 66. 接口名称：kdj实时数据
**接口ID**: 74
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minMacd?code=600004&cycle=9&cycle1=3&cycle2=3&interval=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minKdj",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟kdj数据，金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：间隔周期内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期",
    "name": "cycle",
    "type": "int",
    "default": "9",
    "example": "9",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "3",
    "example": "3",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "3",
    "example": "3",
    "required": "是"
  },
  {
    "desc": "时间间隔：5分钟，15分钟，30分钟，60分钟，120分钟",
    "name": "interval",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "Onject[]",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "k",
    "name": "- k",
    "type": "objec[]",
    "example": "0.39"
  },
  {
    "desc": "d",
    "name": "- d",
    "type": "obejc[]",
    "example": "0.46"
  },
  {
    "desc": "j",
    "name": "- j",
    "type": "object[]",
    "example": "0.138"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "d": [
      1.34
    ],
    "j": [
      3.45
    ],
    "k": [
      4.56
    ],
    "date": [
      "2025-11-04 11:10:00"
    ],
    "api_code": "600004"
  }
}
```

---

## 67. 接口名称：rsi实时数据
**接口ID**: 75
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minRsi?code=600004&cycle1=6&cycle2=12&cycle3=24&interval=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minRsi",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟RSI数据。金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：间隔周期内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "周期3",
    "name": "cycle3",
    "type": "int",
    "default": "24",
    "example": "24",
    "required": "是"
  },
  {
    "desc": "时间间隔：5分钟，15分钟，30分钟，60分钟，120分钟",
    "name": "interval",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "Onject[]",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "rsi1",
    "name": "- rsi1",
    "type": "objec[]",
    "example": "0.39"
  },
  {
    "desc": "rsi2",
    "name": "- rsi2",
    "type": "obejc[]",
    "example": "0.46"
  },
  {
    "desc": "rsi3",
    "name": "- rsi1",
    "type": "object[]",
    "example": "0.18"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "date": [
      "2025-11-04 11:10:00"
    ],
    "rsi1": [
      1.34
    ],
    "rsi2": [
      3.45
    ],
    "rsi3": [
      4.56
    ],
    "api_code": "600004"
  }
}
```

---

## 68. 接口名称：wr实时数据
**接口ID**: 76
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minWr?code=600004&cycle1=10&cycle2=6&interval=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minWr",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟WR数据，金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：周期间隔内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "10",
    "example": "10",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "时间间隔：5分钟，15分钟，30分钟，60分钟，120分钟",
    "name": "interval",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "Onject[]",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "wr1",
    "name": "- wr1",
    "type": "objec[]",
    "example": "0.39"
  },
  {
    "desc": "wr2",
    "name": "- wr2",
    "type": "obejc[]",
    "example": "0.46"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "wr1": [
      3.45
    ],
    "wr2": [
      3.45
    ],
    "date": [
      "2025-11-04 11:10:00"
    ],
    "api_code": "600004"
  }
}
```

---

## 69. 接口名称：cci实时数据
**接口ID**: 77
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minWr",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟WR数据。金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：周期间隔内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
无
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

## 70. 接口名称：bias实时数据
**接口ID**: 78
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/minBias?code=600004&cycle1=6&cycle2=12&cycle3=24&interval=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minBias",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟bias数据。金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：周期间隔内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
[
  {
    "desc": "股票代码",
    "name": "code",
    "type": "string",
    "default": "",
    "example": "601088",
    "required": "是"
  },
  {
    "desc": "周期1",
    "name": "cycle1",
    "type": "int",
    "default": "6",
    "example": "6",
    "required": "是"
  },
  {
    "desc": "周期2",
    "name": "cycle2",
    "type": "int",
    "default": "12",
    "example": "12",
    "required": "是"
  },
  {
    "desc": "周期3",
    "name": "cycle3",
    "type": "int",
    "default": "24",
    "example": "24",
    "required": "是"
  },
  {
    "desc": "时间间隔：5分钟，15分钟，30分钟，60分钟，120分钟",
    "name": "interval",
    "type": "string",
    "default": "5",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- api_code",
    "type": "string",
    "example": "600004"
  },
  {
    "desc": "时间",
    "name": "- date",
    "type": "Onject[]",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "bias12",
    "name": "- bias12",
    "type": "objec[]",
    "example": "0.39"
  },
  {
    "desc": "bias6",
    "name": "- bias6",
    "type": "obejc[]",
    "example": "0.46"
  },
  {
    "desc": "bias24",
    "name": "- bias24",
    "type": "object[]",
    "example": "0.18"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "date": [
      "2025-11-04 11:10:00"
    ],
    "bias6": [
      1.34
    ],
    "bias12": [
      3.45
    ],
    "bias24": [
      4.56
    ],
    "api_code": "600004"
  }
}
```

---

## 71. 接口名称：boll实时数据
**接口ID**: 79
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minWr",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟boll数据。金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：周期间隔内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
无
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

## 72. 接口名称：ma实时数据
**接口ID**: 80
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/minWr",
  "i_desc": "接口说明：查询实时5分钟，15分钟，30分钟，600分钟，120分钟ma数据，金刚钻可用",
  "req_rate": "请求频率: 1次/5分钟起",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：周期间隔内更新，只在9点30至15点之间有数据"
}
```

### 请求参数
```json
无
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

## 73. 接口名称：热点板块
**接口ID**: 81
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/hotBkJlrDr?date=2025-11-14&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/hotBkJlrDr",
  "i_desc": "接口说明：可查询当前主力聚焦的热点板块排行。金刚钻可用",
  "req_rate": "请求频率: 10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午16点"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2025-11-14",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "801004"
  },
  {
    "desc": "板块名称",
    "name": "- bkName",
    "type": "String",
    "example": "锂电池"
  },
  {
    "desc": "涨幅",
    "name": "- qjzf",
    "type": "String",
    "example": "0.4"
  },
  {
    "desc": "涨幅差",
    "name": "- diffQjzf",
    "type": "String",
    "example": "0.4"
  },
  {
    "desc": "净额",
    "name": "- qjje",
    "type": "String",
    "example": "0.4"
  },
  {
    "desc": "净额差",
    "name": "- diffQjje",
    "type": "String",
    "example": "0.4"
  },
  {
    "desc": "资金净流入天数",
    "name": "- jlrts",
    "type": "String",
    "example": "2"
  },
  {
    "desc": "板块强度",
    "name": "- qiangdu",
    "type": "String",
    "example": "29576"
  },
  {
    "desc": "板块强度差",
    "name": "- diffQiangdu",
    "type": "String",
    "example": "576"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": "2025-11-14"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "id": 211,
      "qjje": 4987191157,
      "qjzf": 1.53,
      "time": "2025-11-14",
      "jlrts": 1,
      "bkCode": "801004",
      "bkName": "锂电池",
      "qiangdu": 29576.2,
      "diffQjje": -3653424711,
      "diffQjzf": -1.49,
      "diffQiangdu": 1059.9000000000017
    }
  ]
}
```

---

## 74. 接口名称：热点板块龙头股
**接口ID**: 82
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/hotBkJlrLongTou?date=2025-11-14&plateId=801004&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/hotBkJlrLongTou",
  "i_desc": "接口说明：可查询当前板块下的龙头股，别的都不要，只要龙头。金刚钻可用",
  "req_rate": "请求频率: 10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午16点"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2025-11-14",
    "required": "是"
  },
  {
    "desc": "板块id",
    "name": "plateId",
    "type": "string",
    "default": "",
    "example": "87983",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "板块代码",
    "name": "- bkCode",
    "type": "string",
    "example": "801004"
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "String",
    "example": "002083"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": "孚日股份"
  },
  {
    "desc": "5日区间涨幅",
    "name": "- qjzf",
    "type": "String",
    "example": "61.23"
  },
  {
    "desc": "板块",
    "name": "- bk",
    "type": "String",
    "example": "电解液、服装家纺"
  },
  {
    "desc": "jlrts",
    "name": "- 资金净流入天数",
    "type": "String",
    "example": "3"
  },
  {
    "desc": "资金净流入天数",
    "name": "- jlrts",
    "type": "String",
    "example": "2"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": "2025-11-14"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "bk": "电解液、服装家纺",
      "id": 388,
      "code": "002083",
      "name": "孚日股份",
      "qjzf": 61.23,
      "time": "2025-11-14",
      "jlrts": 4,
      "bkCode": "801004"
    }
  ]
}
```

---

## 75. 接口名称：强势股多日涨幅累计
**接口ID**: 83
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/kplZhangfuRanking?date=2025-11-14&days=5&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/kplZhangfuRanking",
  "i_desc": "接口说明：可查询当前5日，10日累计涨幅最靠前的前50只强势票。金刚钻可用",
  "req_rate": "请求频率: 10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午16点"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2025-11-14",
    "required": "是"
  },
  {
    "desc": "天数(5或10)",
    "name": "days",
    "type": "string",
    "default": "",
    "example": "5",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "String",
    "example": "002083"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "String",
    "example": "孚日股份"
  },
  {
    "desc": "5日或10日区间涨幅",
    "name": "- zf",
    "type": "String",
    "example": "61.23"
  },
  {
    "desc": "板块",
    "name": "- bk",
    "type": "String",
    "example": "电解液、服装家纺"
  },
  {
    "desc": "股价",
    "name": "- price",
    "type": "String",
    "example": "3"
  },
  {
    "desc": "5日或10日资金净流入天数",
    "name": "- jlrts",
    "type": "String",
    "example": "2"
  },
  {
    "desc": "5日或10日净额",
    "name": "- je",
    "type": "String",
    "example": "39999999"
  },
  {
    "desc": "换手率",
    "name": "- hsl换手率",
    "type": "String",
    "example": "119"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "String",
    "example": "2025-11-14"
  },
  {
    "desc": "主力",
    "name": "- zl",
    "type": "String",
    "example": "游资"
  },
  {
    "desc": "类型",
    "name": "- type",
    "type": "String",
    "example": "5日或者10日"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "bk": "电解液、服装家纺",
      "je": 239811665,
      "zf": 61.23,
      "zl": "游资",
      "hsl": 4016167939,
      "code": "002083",
      "name": "孚日股份",
      "type": 5,
      "jlrts": 4,
      "price": 11.56
    }
  ]
}
```

---

## 76. 接口名称：月游资排行榜单
**接口ID**: 84
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/youziRank?startDate=2026-02-26&endDate=2026-03-26&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/youziRank",
  "i_desc": "接口说明，查询最近一个月的游资上榜排行次数。",
  "req_rate": "请求频率: 10次/秒",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午18点"
}
```

### 请求参数
```json
[
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2026-02-26",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2026-03-26",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "上榜次数",
    "name": "- num",
    "type": "string",
    "example": "10"
  },
  {
    "desc": "游资营业部",
    "name": "- yybName",
    "type": "string",
    "example": "2025-11-04 11:00:00"
  },
  {
    "desc": "游资名称",
    "name": "- groupIcon",
    "type": "string",
    "example": "量化基金"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "num": 69,
      "yybName": "开源证券西安太华路",
      "groupIcon": "[\"量化打板\"]"
    }
  ]
}
```

---

## 77. 接口名称：最近游资活跃股
**接口ID**: 85
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/activeYouziStocks?tradeDate=2026-03-25&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/activeYouziStocks",
  "i_desc": "接口说明，查询最近五日各大游资买入金额大于8千万且关注度比较高的票",
  "req_rate": "请求频率: 10次/天",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午18点"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2026-02-26",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态信息",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "数据列表",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "较昨日总次数变化",
    "name": "- diff_total_count",
    "type": "int",
    "example": "0"
  },
  {
    "desc": "所属板块",
    "name": "- bk_info",
    "type": "string",
    "example": "绿色电力、算力"
  },
  {
    "desc": "总净额（格式化）",
    "name": "- total_je_formatted",
    "type": "string",
    "example": "-7.68亿"
  },
  {
    "desc": "较昨日大于8000万营业部个数变化",
    "name": "- diff_big_yyb_count",
    "type": "int",
    "example": "-1"
  },
  {
    "desc": "股票代码",
    "name": "- code",
    "type": "string",
    "example": "600821"
  },
  {
    "desc": "大于8000万营业部总次数",
    "name": "- big_count",
    "type": "int",
    "example": "15"
  },
  {
    "desc": "大于8000万营业部个数",
    "name": "- big_yyb_count",
    "type": "int",
    "example": "10"
  },
  {
    "desc": "总上榜次数",
    "name": "- total_count",
    "type": "int",
    "example": "39"
  },
  {
    "desc": "股票名称",
    "name": "- name",
    "type": "string",
    "example": "金开新能"
  },
  {
    "desc": "较昨日大于8000万总次数变化",
    "name": "- diff_big_count",
    "type": "int",
    "example": "-2"
  },
  {
    "desc": "较昨日营业部个数变化",
    "name": "- diff_yyb_count",
    "type": "int",
    "example": "0"
  },
  {
    "desc": "营业部个数",
    "name": "- yyb_count",
    "type": "int",
    "example": "19"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "code": "600821",
      "name": "金开新能",
      "bk_info": "绿色电力、算力",
      "big_count": 15,
      "yyb_count": 19,
      "total_count": 39,
      "big_yyb_count": 10,
      "diff_big_count": -2,
      "diff_yyb_count": 0,
      "diff_total_count": 0,
      "diff_big_yyb_count": -1,
      "total_je_formatted": "-7.68亿"
    }
  ]
}
```

---

## 78. 接口名称：板块/概念/地域资金流
**接口ID**: 86
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/blockFundFlow?prodType=HY&date=2026-07-31&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/blockFundFlow",
  "i_desc": "接口说明，查询板块、概念、地域资金流,黄金套餐可用",
  "req_rate": "请求频率: 10次/s",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午16:30点"
}
```

### 请求参数
```json
[
  {
    "desc": "板块类型(HY/GN/DY)黄金套餐可用",
    "name": "prodType",
    "type": "string",
    "default": "HY",
    "example": "HY",
    "required": "是"
  },
  {
    "desc": "时间",
    "name": "date",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- prodCode",
    "type": "string",
    "example": "270100"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "半导体"
  },
  {
    "desc": "涨跌幅",
    "name": "- pxChangeRatio",
    "type": "string",
    "example": "-1.38"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "10.73"
  },
  {
    "desc": "特大单净流入",
    "name": "- superGrpPureIn",
    "type": "string",
    "example": "-1.5245291E7"
  },
  {
    "desc": "大单净流入",
    "name": "- largeGrpPureIn",
    "type": "string",
    "example": "-17.6"
  },
  {
    "desc": "中单净流入",
    "name": "- mediumGrpPureIn",
    "type": "string",
    "example": "-8549201.0"
  },
  {
    "desc": "小单净流入",
    "name": "- littleGrpPureIn",
    "type": "string",
    "example": "-9.87"
  },
  {
    "desc": "主力净流入",
    "name": "- pureIn",
    "type": "string",
    "example": "-6696090.0"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "name": "半导体",
      "time": "2026-07-31",
      "pureIn": 9482312742,
      "prodCode": "270100",
      "prodType": "HY",
      "lastPrice": 4220040,
      "pxChangeRatio": 417,
      "largeGrpPureIn": -4223658656,
      "superGrpPureIn": 13705971398,
      "littleGrpPureIn": -627455465,
      "mediumGrpPureIn": -8893495817
    }
  ]
}
```

---

## 79. 接口名称：板块/概念/地域历史资金流
**接口ID**: 87
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/blockFundFlowHistory?prodCode=GN030008&startDate=2026-07-31&endDate=2026-07-31&pageNo=1&pageSize=100&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/blockFundFlowHistory",
  "i_desc": "接口说明，查询板块、概念、地域历史资金流，黄金套餐可用",
  "req_rate": "请求频率: 10次/s",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日下午16:30点"
}
```

### 请求参数
```json
[
  {
    "desc": "板块/概念/地域代码(黄金套餐可用)",
    "name": "prodCode",
    "type": "string",
    "default": "GN030008",
    "example": "HY",
    "required": "是"
  },
  {
    "desc": "开始时间",
    "name": "startDate",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  },
  {
    "desc": "结束时间",
    "name": "endDate",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  },
  {
    "desc": "页码",
    "name": "pageNo",
    "type": "string",
    "default": "1",
    "example": "1",
    "required": "是"
  },
  {
    "desc": "每页行数",
    "name": "pageSize",
    "type": "string",
    "default": "100",
    "example": "100",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "代码",
    "name": "- prodCode",
    "type": "string",
    "example": "270100"
  },
  {
    "desc": "名称",
    "name": "- name",
    "type": "string",
    "example": "半导体"
  },
  {
    "desc": "涨跌幅",
    "name": "- pxChangeRatio",
    "type": "string",
    "example": "-1.38"
  },
  {
    "desc": "最新价",
    "name": "- lastPrice",
    "type": "string",
    "example": "10.73"
  },
  {
    "desc": "特大单净流入",
    "name": "- superGrpPureIn",
    "type": "string",
    "example": "-1.5245291E7"
  },
  {
    "desc": "大单净流入",
    "name": "- largeGrpPureIn",
    "type": "string",
    "example": "-17.6"
  },
  {
    "desc": "中单净流入",
    "name": "- mediumGrpPureIn",
    "type": "string",
    "example": "-8549201.0"
  },
  {
    "desc": "小单净流入",
    "name": "- littleGrpPureIn",
    "type": "string",
    "example": "-9.87"
  },
  {
    "desc": "主力净流入",
    "name": "- pureIn",
    "type": "string",
    "example": "-6696090.0"
  },
  {
    "desc": "时间",
    "name": "- time",
    "type": "string",
    "example": "2023-09-01"
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": {
    "pages": 1,
    "total": 1,
    "current": 1,
    "records": [
      {
        "name": "半导体",
        "time": "2026-07-31",
        "pureIn": 9482312742,
        "prodCode": "270100",
        "prodType": "HY",
        "lastPrice": 4220040,
        "pxChangeRatio": 417,
        "largeGrpPureIn": -4223658656,
        "superGrpPureIn": 13705971398,
        "littleGrpPureIn": -627455465,
        "mediumGrpPureIn": -8893495817
      }
    ]
  }
}
```

---

## 80. 接口名称：早盘股市新闻
**接口ID**: 88
**版本**: -

### 接口地址
**有Token示例**: `https://www.stockapi.com.cn/v1/base/queryXgbNews?tradeDate=2026-07-31&token=你的token`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.stockapi.com.cn/v1/base/queryXgbNews",
  "i_desc": "接口说明，查询早盘股市新闻信息",
  "req_rate": "请求频率: 10次/s",
  "res_format": "请求方式：GET",
  "update_rate": "更新时间：交易日上午8:30点"
}
```

### 请求参数
```json
[
  {
    "desc": "时间",
    "name": "tradeDate",
    "type": "string",
    "default": "",
    "example": "2026-07-31",
    "required": "是"
  }
]
```

### 返回参数说明
```json
[
  {
    "desc": "返回码",
    "name": "code",
    "type": "int",
    "example": "20000"
  },
  {
    "desc": "状态",
    "name": "msg",
    "type": "string",
    "example": "success"
  },
  {
    "desc": "",
    "name": "data",
    "type": "Object[]",
    "example": ""
  },
  {
    "desc": "摘要",
    "name": "- summary",
    "type": "string",
    "example": ""
  },
  {
    "desc": "新闻发布时间",
    "name": "- createdAt",
    "type": "string",
    "example": ""
  },
  {
    "desc": "新闻内容",
    "name": "- articleContent",
    "type": "string",
    "example": ""
  },
  {
    "desc": "新闻标题",
    "name": "- title",
    "type": "string",
    "example": ""
  }
]
```

### 返回示例
```json
{
  "msg": "success",
  "code": 20000,
  "data": [
    {
      "title": "7月31日早餐 | 美股科技股大幅反弹；宇树科技申购定档",
      "summary": "纳指涨2.8%终结六连跌，芯片指数暴力反弹17%；政治局会议部署下半年经济工作，宏观政策发力提效；何立峰与美财长通话；苹果盘后跌7%，亚马逊盘后涨10%。",
      "createdAt": "2026-07-31 07:57:27",
      "articleContent": "# 7月31日早餐 | 美股科技股大幅反弹；宇树科技申购定档\n\n2026/07/30 23:57\n\n---\n\n\n\n```\n纳指涨2.8%终结六连跌，芯片指数暴力反弹17%；政治局会议部署下半年经济工作，宏观政策发力提效；何立峰与美财长通话；苹果盘后跌7%，亚马逊盘后涨10%。\n```\n\n\n\n**先看海外要闻：**\n\n\n\n> \n\n隔夜美股标普500涨幅1.66%，道指涨幅1.19%，纳指涨幅2.78%，纳指终结六连跌。\n\n\n\n美股存储芯片指数收涨16.93%，暴力反弹。闪迪收涨26%，美光科技涨逾18%，SK海力士ADR涨17.5%，西部数据涨超11%。\n\n\n\n费城半导体指数涨超8%，Lumentum涨超15%，Credo涨超13%，Coherent涨超12%，微软涨超15%、创2008年10月以来最大单日涨幅，AMD涨超13%，AXT、Nebius涨约27%。\n\n\n\nWTI 9月原油期货收跌1.03%，布伦特9月原油期货收跌1.88%，现货黄金涨0.81%，报4100.34美元/盎司，现货白银涨2.07%，报58.93美元/盎司。\n\n\n\n纳斯达克金龙中国指数收涨1.05%。中概股方面，世纪互联涨16.7%，日月光半导体涨12.2%，万国数据涨8%，[阿特斯](https://xuangutong.com.cn/stock/688472.SS)[太阳能](https://xuangutong.com.cn/stock/000591.SZ)涨7.7%。\n\n\n\n美国二季度GDP年化增长1.5%不及预期，6月PCE物价指数六年来首次环比下降。英国央行如期维持利率3.75%不变。\n\n\n\n日本政府实施汇市干预，日元兑美元盘中暴涨逾3%，一度涨穿158日元。离岸人民币创2023年初以来新高。\n\n\n\n苹果第三财季营收1094.2亿美元超预期，但预计第四财季营收增长9%-11%低于分析师预期的12.1%，盘后跌7%。上季iPhone收入增22%略超预期，但服务和中国市场业绩逊色。\n\n\n\n亚马逊二季度净销售2006亿美元超预期，高管预计2026年资本开支2200亿美元主要用于AI，盘后涨超10%。\n\n\n\n美多名议员阻挠苹果采购中国芯片，专家：将破坏中美企业产业链合作。\n\n\n\nOpenAI推出GPT-5.6“促销”：Luna降价80%，Sol首推2.5倍速“反向加价”模式。\n\n\n\n谷歌发布新一代[机器人](https://xuangutong.com.cn/stock/300024.SZ)AI模型，实现人形[机器人](https://xuangutong.com.cn/stock/300024.SZ)全身控制。\n\n\n\n\n\n**国内重大事件汇总：**\n\n\n\n> \n\n1、中共中央政治局7月30日召开会议，分析研究当前经济形势，部署下半年经济工作。会议强调，宏观政策要发力提效，务实管用的增量政策可期；深化资本市场投融资综合改革，提升资本市场韧性和信心。\n\n\n\n2、何立峰与美国财政部长贝森特、贸易代表格里尔举行视频通话。\n\n\n\n3、商务部：中欧初步商定今年秋季举行磋商机制第二次会议。\n\n\n\n4、我国加快形成扩大居民消费长效机制观察。\n\n\n\n5、国家广播电视总局联合工业和信息化部召开一体化电视全国推广工作部署会。\n\n\n\n6、农业农村部：研发农业农村专业模型，加快突破农业传感器等领域关键核心技术。\n\n\n\n7、上海市人民政府印发《上海市卫生健康发展“十五五”规划》。\n\n\n\n8、工信部量子信息标准化技术委员会成立。\n\n\n\n9、北交所召开公募基金座谈会听取意见建议。\n\n\n\n10、第12批国家组织药品集采将在上海开标。国家药监局批准4款创新药上市。\n\n\n\n11、7月初以来，我国用电负荷三创历史新高，迎峰度夏电力保供进入关键阶段。\n\n\n\n12、算力金属”价格狂飙，铜、铝、锡、钽、铟等有色金属价格大幅上涨，锡价半年内上涨40%，钽价更是飙升158%，铟价上涨60%。\n\n\n\n13、预售价29.99万元！小米澎程N90 Max最高续航1705公里，“从上海开到北京不用充电加油”。\n\n\n\n14、特斯拉全球第1000万辆电动车下线，上海超级工厂上半年产量创新高。\n\n\n\n15、消息称字节已组建豆包办公部门。\n\n\n\n16、[宇树科技](https://xuangutong.com.cn/stock/688836.SS)：初步询价日为8月5日，网上网下申购日为8月10日。\n\n\n\n\n\n**今日题材方面：**\n\n\n\n> \n\n**1、人工智能丨**据7月30日报道，字节跳动正在内部组建\"豆包办公\"独立部门，将字节旗下办公协作类产品（飞书）及豆包AI底层能力进行深度融合，推出面向企业客户的AI办公套件。字节此前已先后推出飞书智能伙伴、豆包智能文档助手等AI办公产品。\n\n\n\n点评：AI办公赛道正从\"回答问题\"向\"完成任务\"跃迁。随着大模型上下文窗口、推理能力持续提升，AI不仅能处理信息检索，还能直接生成报告、整理会议纪要、自动填写表单等，企业级AI办公市场空间广阔。字节将豆包AI与飞书深度整合，意味着其AI战略正从C端消费级应用加速向B端企业级应用拓展，与微软Copilot、谷歌Workspace AI等形成对标。\n\n\n\n** 2、量子通信丨**7月30日，工信部发布通知，决定成立\"量子信息技术标准化技术委员会\"，旨在加快布局量子信息技术领域标准化工作，推动量子计算、量子通信、量子精密测量等产业化进程。\n\n\n\n点评：量子信息技术标准化技术委员会的成立，标志着我国量子科技产业化进入标准引领的新阶段。标准化是技术从实验室走向产业化规模应用的关键环节，尤其在量子计算、量子通信等前沿领域，标准的制定有助于统一技术路线、加速产业链协同、降低商业化应用门槛。此前我国已在量子通信领域取得多项国际领先成果，随着标准化体系建立，量子信息技术有望加速向金融、政务、能源等领域渗透。\n\n\n\n** 3、[机器人](https://xuangutong.com.cn/stock/300024.SZ)丨**据7月30日报道，京东与七腾[机器人](https://xuangutong.com.cn/stock/300024.SZ)达成战略合作，双方将围绕具身智能应用落地、仓储自动化及物流[机器人](https://xuangutong.com.cn/stock/300024.SZ)技术创新等领域展开深度合作。京东物流此前已广泛部署仓储分拣、配送等环节的[机器人](https://xuangutong.com.cn/stock/300024.SZ)应用。\n\n\n\n点评：继[比亚迪](https://xuangutong.com.cn/stock/002594.SZ)、小鹏、理想等车企跨界入局后，电商物流巨头也加速切入[机器人](https://xuangutong.com.cn/stock/300024.SZ)赛道。京东物流场景天然适配仓储分拣、末端配送等[机器人](https://xuangutong.com.cn/stock/300024.SZ)应用，与七腾[机器人](https://xuangutong.com.cn/stock/300024.SZ)合作将推动人形/具身[机器人](https://xuangutong.com.cn/stock/300024.SZ)在物流场景的商业化落地。今年来国内工业[机器人](https://xuangutong.com.cn/stock/300024.SZ)产量持续高增，产业链从上游核心零部件到下游应用场景全面受益。\n\n\n\n** 4、东数西算/算力丨**据7月30日数据，AI算力需求持续火爆推动存储产品和显卡价格攀升。SK海力士已开始大规模发货HBM4，全球AI服务器对高带宽存储的强劲需求推动存储芯片价格持续上涨。美光、三星等大厂积极扩产应对AI算力需求。\n\n\n\n点评：AI大模型训练和推理对算力的需求正以指数级增长，带动服务器、存储、GPU等硬件需求井喷。亚马逊预计2026年资本开支达2200亿美元主要用于AI，微软新增数据中心租约超1300亿美元，全球科技巨头AI军备竞赛持续加码。高端算力供不应求，部分企业甚至探索\"Token工厂\"新模式，按算力使用量计费，AI算力正成为新时代的核心基础设施。\n\n\n\n\n\n**今日有2只新股申购：**\n\n\n\n> \n\n[超纯应材](https://xuangutong.com.cn/stock/301717.SZ)：创业板，申购价格65.99元/股，顶格申购需配市值5万元。公司半导体设备特殊涂层零部件本土企业市场份额排名第一。\n\n\n\n[国仪公司](https://xuangutong.com.cn/stock/688828.SS)：科创板，申购价格21.22元/股，顶格申购需配市值6万元。公司是我国高端科学仪器本土核心供应商，多款量子科学仪器为国内独家或国内外首台套。\n\n\n\n\n\n**再来看上市公司公告精华：**\n\n\n\n> \n\n1、富淼科技：拟以6.96亿元收购沃特泰科51.16%股权，将其纳入合并报表。\n\n\n\n2、长飞光纤：拟以1200万欧元收购Draka持有的长飞上海25%股权，完成后将全资控股。\n\n\n\n3、宇晶股份：拟定增募资1.76亿元，用于大尺寸硅片及碳化硅设备等项目。\n\n\n\n4、东阳光：控股股东提议以3亿元至6亿元回购股份；控股股东拟增持3亿元至6亿元。\n\n\n\n5、网宿科技：拟以3亿元至6亿元回购股份，回购价不超21.17元/股，用于注销。\n\n\n\n6、渤海租赁：拟以2亿元回购股份，回购价不超6.48元/股。\n\n\n\n7、恒通股份：南山集团拟增持1亿元，SONG JIANBO拟增持5000万元。\n\n\n\n8、甬矽电子：实控人提议以1亿元至1.5亿元回购股份。\n\n\n\n9、超达装备：拟将回购金额上调至5000万元至1亿元。\n\n\n\n10、广东宏大：董事长提议以5000万元至1亿元回购股份。\n\n\n\n11、乐鑫科技：拟以5000万元至1亿元回购股份，回购价不超121.28元/股。\n\n\n\n12、中研股份：拟以5000万元至1亿元回购股份，回购价不超48.94元/股。\n\n\n\n13、容百科技：拟投建仙桃年产30万吨钠电正极材料一体化项目，总投资47.23亿元。\n\n\n\n14、索菱股份：子公司与三菱重工签订电子设备供货合同，总价1.3亿美元。\n\n\n\n15、铂力特：拟与关联方正时精控签订采购框架合同，金额约1.51亿元。\n\n\n\n16、长春高新：子公司GenSci144片临床试验获批。\n\n\n\n17、百利天恒：注射用BL-B01D1（皮下注射）治疗晚期实体瘤临床试验获批。\n\n\n\n18、亚翔集成：上半年净利润4.9亿元，同比增长204.8%。\n\n\n\n19、华资实业：股东世通投资拟减持不超3%。\n\n\n\n\n\n\n\n![](https://image.xuangubao.com.cn/FjQjMrsJjV5iU2UqOiFc3iolAfwQ)\n\n\n\n\n\n\n\n![](https://image.xuangubao.com.cn//Flzgvo3raU0sL6wad7Q6vX-YPXPt)\n\n\n\n\n\n*"
    }
  ]
}
```

---

## 81. 接口名称：文件转为Markdown
**接口ID**: 89
**版本**: -

### 接口地址
**有Token示例**: `-`

### 接口说明
```json
{
  "i_url": "接口地址：https://www.skillsbot.cn/skillv3/api/markitdown/convert/file",
  "i_desc": "接口说明，上传文件并转换为 Markdown（JSON 格式返回）,支持格式: PDF, DOCX, PPTX, XLSX, XLS, HTML, CSV, EPUB, 图片, 音频, ZIP 等",
  "req_rate": "请求频率: 10次/s",
  "res_format": "请求方式：GET",
  "update_rate": "扣费说明：每次扣0.2元"
}
```

### 请求参数
```json
[
  {
    "desc": "文件：支持格式: PDF, DOCX, PPTX, XLSX, XLS, HTML, CSV, EPUB, 音频, ZIP 等",
    "name": "file",
    "type": "file",
    "default": "",
    "example": "券商研报.PDF",
    "required": "是"
  }
]
```

### 返回参数说明
```json
无
```

### 返回示例
```json
无
```

---

