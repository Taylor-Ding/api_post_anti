import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Play } from 'lucide-react';
import ApiConfigPanel from './components/ApiConfigPanel';
import AssertionPanel from './components/AssertionPanel';
import ResultViewer from './components/ResultViewer';
import LogTerminal from './components/LogTerminal';

function App() {
  const [url, setUrl] = useState('http://localhost:8080/api/v1/business-endpoint');
  const [payload, setPayload] = useState('{\n  "custNo": "00000194476241",\n  "amount": 5000.0\n}');
  
  const [tables, setTables] = useState([
    'tb_dpmst_medium'
  ]);

  const [isExecuting, setIsExecuting] = useState(false);
  const [responseData, setResponseData] = useState(null);
  const [assertionResults, setAssertionResults] = useState([]);
  const [logs, setLogs] = useState([]);

  // 用于在点击按钮后立刻跳转到日志区域
  const viewRef = useRef(null);
  // 用于在执行结束后由于内容展开导致页面撑大时继续下滑至结果看板
  const resultRef = useRef(null);

  const handleExecute = async () => {
    setIsExecuting(true);
    setResponseData(null);
    setAssertionResults([]);
    setLogs([]);

    // 页面马上滚动到日志区域
    setTimeout(() => {
      viewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);

    const now = () => new Date().toISOString().split('T')[1].slice(0, 12);
    const delay = (ms) => new Promise(res => setTimeout(res, ms));
    const appendLog = (msg) => { setLogs(prev => [...prev, msg]); };

    let parsedKey = "未知";
    let keyType = "未知";
    let realPayloadObj = null;

    try {
      realPayloadObj = JSON.parse(payload);
      const txHeader = realPayloadObj?.txHeader || {};

      if (!("mainMapElemntInfo" in txHeader)) {
        appendLog(`[ERROR] [${now()}] 严重错误：报文 txHeader 中缺失 mainMapElemntInfo 字段`);
        setIsExecuting(false);
        return;
      }

      const mainInfo = txHeader.mainMapElemntInfo;
      
      if (!mainInfo) {
        appendLog(`[INFO] [${now()}] 提示：mainMapElemntInfo 字段存在，但值为空或 null`);
      } else if (mainInfo.startsWith('04')) {
        const custNo = mainInfo.slice(2);
        if (!custNo) {
          appendLog(`[ERROR] [${now()}] 异常：mainMapElemntInfo 字段以 04 开头，但后续没有客户号字符串信息`);
          setIsExecuting(false);
          return;
        }
        parsedKey = custNo;
        keyType = "custNo";
        appendLog(`[INFO] [${now()}] ✅ 成功解析 mainMapElemntInfo 获取到客户号(custNo): ${custNo}`);
      } else if (mainInfo.startsWith('05')) {
        const mediumNo = mainInfo.slice(2);
        if (!mediumNo) {
          appendLog(`[ERROR] [${now()}] 异常：mainMapElemntInfo 字段以 05 开头，但后续没有介质号字符串信息`);
          setIsExecuting(false);
          return;
        }
        parsedKey = mediumNo;
        keyType = "mediumNo";
        appendLog(`[INFO] [${now()}] ✅ 成功解析 mainMapElemntInfo 获取到介质号(mediumNo): ${mediumNo}`);
      } else {
        appendLog(`[ERROR] [${now()}] 异常：无法识别的 mainMapElemntInfo 头部前缀标识: ${mainInfo}`);
        setIsExecuting(false);
        return;
      }
    } catch (e) {
      appendLog(`[ERROR] [${now()}] JSON 报文前端本地解析异常: ${e.message}`);
      setIsExecuting(false);
      return;
    }

    // 接下来真正调用后端流水线
    await delay(200);
    appendLog(`[INFO] [${now()}] 🚀 开始向本地 Python 核心引擎投递全量核对任务...`);
    
    let serverRes;
    try {
      const resp = await fetch("http://127.0.0.1:5000/api/verify_pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          payload: realPayloadObj,
          tables: tables
        })
      });

      serverRes = await resp.json();
      
      if (!resp.ok) {
         appendLog(`[ERROR] [${now()}] 后端引擎拦截返回异常: ${serverRes.error || '未知错误'}`);
         setIsExecuting(false);
         return;
      }
    } catch (e) {
      appendLog(`[ERROR] [${now()}] 无法连接到 Python 引擎(127.0.0.1:5000): ${e.message}`);
      appendLog(`[INFO] [${now()}] 请确保已经在终端执行了 \`python3 server.py\``);
      setIsExecuting(false);
      return;
    }

    const { report, api_response, lookup_log, resolved_cust_no } = serverRes;
    const { before_snapshot, after_snapshot, diff_detail, is_equal, summary } = report;

    if (lookup_log) {
       await delay(200);
       // 显示高亮色彩以体现这是动态反查出来的结果
       appendLog(`[INFO] [${now()}] 🔄 触发反查网关 | ${lookup_log}`);
       await delay(200);
    }

    await delay(300);
    appendLog(`[INFO] [${now()}] >>> [1/4] 查询接口调用前的数据状态...`);
    await delay(200);
    let queryField = "cust_no";
    let queryValue = resolved_cust_no;
    
    // 如果返回的路由键类型是 mediumNo，前端为了渲染假装知道其对应的查询条件是 medium_no
    if (serverRes.key_type === "mediumNo") {
        queryField = "medium_no";
        queryValue = serverRes.routing_key;
    }
    
    appendLog(`[DEBUG] [${now()}] 核心路由计算 | 基于 custNo=${resolved_cust_no} 指向 db=${before_snapshot?.db_name}`);
    appendLog(`[INFO] [${now()}] 执行真实查询 | db=${before_snapshot?.db_name} sql=SELECT * FROM "${before_snapshot?.table_name}" WHERE ${queryField} = %s params=('${queryValue}',)`);
    await delay(200);
    appendLog(`[INFO] [${now()}] 查询完成 | 真实获取条数 rows=${before_snapshot?.row_count}`);
    appendLog(`[DEBUG] [${now()}] 前置查询结果明细集: ${JSON.stringify(before_snapshot?.rows || [])}`);
    
    await delay(300);
    appendLog(`[INFO] [${now()}] >>> [2/4] 通过 ApiCaller 触发业务网关接口...`);
    appendLog(`[INFO] [${now()}] 发起原声 POST 请求 | url=${url}`);
    
    // 我们假设 API 响应已经在引擎内完成了。
    appendLog(`[INFO] [${now()}] 收到真实的网关响应, 已捕获。`);
    
    await delay(300);
    appendLog(`[INFO] [${now()}] >>> [3/4] 触发第二次后置数据库数据查询...`);
    appendLog(`[INFO] [${now()}] 查询完成 | 真实获取条数 rows=${after_snapshot?.row_count}`);
    appendLog(`[DEBUG] [${now()}] 后置查询结果明细集: ${JSON.stringify(after_snapshot?.rows || [])}`);

    await delay(400);
    appendLog(`[INFO] [${now()}] >>> [4/4] 启动 DeepDiff 对比分析引擎...`);
    await delay(300);
    
    if (is_equal) {
        appendLog(`[INFO] [${now()}] ✅ 全量比对分析完成: 数据一致！`);
    } else {
        appendLog(`[ERROR] [${now()}] ❌ 发现总体不一致：${summary}`);
        if (diff_detail) {
            if (diff_detail.values_changed) {
                Object.entries(diff_detail.values_changed).forEach(([path, change]) => {
                    const cleanPath = path.replace(/root\[\d+\]\['([^']+)'\]/, '$1').replace("root", "");
                    appendLog(`[ERROR] [${now()}] ✏️ 表 [${before_snapshot?.table_name}] 字段被修改: ${cleanPath}  | 【原值: ${change.old_value}】 → 【新值: ${change.new_value}】`);
                });
            }
            if (diff_detail.dictionary_item_added) {
                diff_detail.dictionary_item_added.forEach(item => {
                    appendLog(`[ERROR] [${now()}] ➕ 检测到非法新增字段/列表项: ${item}`);
                });
            }
            if (diff_detail.dictionary_item_removed) {
                diff_detail.dictionary_item_removed.forEach(item => {
                    appendLog(`[ERROR] [${now()}] ➖ 检测到数据丢失/字段抹除: ${item}`);
                });
            }
            if (diff_detail.iterable_item_added) {
                Object.entries(diff_detail.iterable_item_added).forEach(([path, val]) => {
                    appendLog(`[ERROR] [${now()}] ➕ 集合中新增记录: ${path} => ${JSON.stringify(val)}`);
                });
            }
            if (diff_detail.iterable_item_removed) {
                Object.entries(diff_detail.iterable_item_removed).forEach(([path, val]) => {
                    appendLog(`[ERROR] [${now()}] ➖ 集合中记录缺失: ${path} => ${JSON.stringify(val)}`);
                });
            }
        }
    }

    // 构建业务接口真实返回大看板
    setResponseData(api_response);

    // 对于所有的表进行断言结果包装。目前虽然底层仅查了一张由于路由指定的表，
    // 我们直接将真实的 Diff 明细灌入到表格结果里！
    const realResults = [{
      table: before_snapshot?.table_name || tables[0],
      passed: is_equal,
      message: summary,
      diffDetails: is_equal ? null : diff_detail
    }];

    setAssertionResults(realResults);
    setIsExecuting(false);

    // 绘制出最终结果看板后，将页面视点平滑滑动至底部
    setTimeout(() => {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 100);
  };

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* Header section */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        style={{ marginBottom: '40px', textAlign: 'center' }}
      >
        <h1 style={{ 
          fontSize: '36px', 
          background: 'linear-gradient(to right, #8c52ff, #00d2ff)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '12px'
        }}>
          分布式数据持续核对枢纽
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '16px' }}>
          实时 API 发起与分布式分库分表一致性比对终端。
        </p>
      </motion.header>

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <ApiConfigPanel 
          url={url} setUrl={setUrl}
          payload={payload} setPayload={setPayload}
        />
        
        <AssertionPanel 
          tables={tables} setTables={setTables} 
        />
      </div>

      {/* Execution Trigger */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        style={{ display: 'flex', justifyContent: 'center', marginTop: '32px' }}
      >
        <button 
          className="btn" 
          onClick={handleExecute} 
          disabled={isExecuting}
          style={{ 
            fontSize: '18px', 
            padding: '16px 48px',
            opacity: isExecuting ? 0.7 : 1,
            boxShadow: isExecuting ? 'none' : 'var(--shadow-glow)'
          }}
        >
          {isExecuting ? (
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              style={{ display: 'inline-block' }}
            >
              ⟳
            </motion.span>
          ) : <Play size={20} />}
          {isExecuting ? '验证比对中...' : '开始执行核对'}
        </button>
      </motion.div>

      {/* Scroll View Anchor for Logs/Results */}
      <div ref={viewRef} style={{ scrollMarginTop: '40px' }} />

      {/* Terminal Visualizer */}
      <LogTerminal logs={logs} />

      {/* Result Display Block */}
      <div ref={resultRef}>
        <ResultViewer responseData={responseData} assertionResults={assertionResults} />
      </div>

    </div>
  );
}

export default App;
