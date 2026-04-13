import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, Code2 } from 'lucide-react';

export default function ResultViewer({ responseData, assertionResults }) {
  if (!responseData && !assertionResults.length) {
    return null;
  }

  const staggeredContainer = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemAnim = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <motion.div 
      className="glass-panel" 
      style={{ marginTop: '24px' }}
      variants={staggeredContainer}
      initial="hidden"
      animate="show"
    >
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Code2 size={22} color="var(--success)" />
          执行结果看板
        </h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Response Block */}
        <motion.div variants={itemAnim}>
          <label>业务接口下发响应</label>
          <div style={{ 
            background: 'rgba(0,0,0,0.4)', 
            padding: '16px', 
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--panel-border)',
            minHeight: '200px',
            overflow: 'auto'
          }}>
            <pre style={{ 
              fontFamily: 'var(--font-mono)', 
              fontSize: '13px', 
              color: 'var(--secondary-color)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              margin: 0
            }}>
              {responseData ? JSON.stringify(responseData, null, 2) : '等待网关响应...'}
            </pre>
          </div>
        </motion.div>

        {/* Assertion Block */}
        <motion.div variants={itemAnim}>
          <label>全分片断言报告</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {assertionResults.length === 0 ? (
              <div style={{ padding: '16px', color: 'var(--text-muted)' }}>未执行任何查核比对。</div>
            ) : (
              assertionResults.map((res, i) => (
                <div key={i} style={{ 
                  background: res.passed ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 61, 113, 0.05)',
                  border: `1px solid ${res.passed ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 61, 113, 0.2)'}`,
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}>
                  <div style={{ paddingTop: '2px' }}>
                    {res.passed ? <CheckCircle2 color="var(--success)" size={20} /> : <XCircle color="var(--error)" size={20} />}
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong style={{ display: 'block', fontSize: '15px', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
                      {res.table}
                    </strong>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                      {res.message}
                    </div>
                    {/* 发生错误且包含了具体 Diff 明细时的折叠渲染区 */}
                    {!res.passed && res.diffDetails && (
                      <div style={{ 
                        marginTop: '12px',
                        background: 'rgba(0,0,0,0.4)',
                        border: '1px solid rgba(255,61,113,0.15)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '12px'
                      }}>
                        <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--error)', marginBottom: '8px', fontWeight: 600 }}>Diff 扫描快照明细</div>
                        <pre style={{ 
                          fontFamily: 'var(--font-mono)', 
                          fontSize: '12px', 
                          color: '#e2e4ed',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                          margin: 0
                        }}>
                          {JSON.stringify(res.diffDetails, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
