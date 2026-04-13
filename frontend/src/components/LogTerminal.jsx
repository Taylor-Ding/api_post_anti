import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Terminal } from 'lucide-react';

export default function LogTerminal({ logs }) {
  const bottomRef = useRef(null);

  // 当产生新日志时，自动滚动到终端底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="glass-panel"
      style={{ marginTop: '24px' }}
    >
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Terminal size={20} color="var(--secondary-color)" />
        <h3 style={{ fontSize: '16px', color: 'var(--text-main)' }}>实时流控日志 (Terminal Trace)</h3>
      </div>
      
      <div 
        style={{
          background: '#040508',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 'var(--radius-sm)',
          height: '280px',
          overflowY: 'auto',
          padding: '16px',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
          lineHeight: '1.6',
          color: '#a9adc1',
          boxShadow: 'inset 0 4px 12px rgba(0,0,0,0.5)'
        }}
      >
        {logs.length === 0 ? (
          <span style={{ color: 'var(--text-muted)' }}>等待执行触发...</span>
        ) : (
          logs.map((log, i) => {
            // 给特殊高亮的日志标签标色
            let color = '#a9adc1';
            if (log.includes('[INFO]')) color = '#00d2ff';
            if (log.includes('[ERROR]')) color = '#ff3d71';
            if (log.includes('[DEBUG]')) color = '#8c52ff';

            return (
              <div key={i} style={{ marginBottom: '4px', wordBreak: 'break-all' }}>
                <span style={{ color, opacity: 0.9 }}>{log}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </motion.div>
  );
}
