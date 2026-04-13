import React from 'react';
import { Network, FileJson } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ApiConfigPanel({ url, setUrl, payload, setPayload }) {
  return (
    <motion.div 
      className="glass-panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-color)' }}>
          <Network size={22} />
          API 请求配置
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          配置将要发送的 POST 请求目标及报文格式。
        </p>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label htmlFor="apiUrl">接口地址 (URL)</label>
        <div style={{ position: 'relative' }}>
          <input
            id="apiUrl"
            type="text"
            className="input-field"
            placeholder="http://localhost:8080/api/v1/business-endpoint"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
      </div>

      <div>
        <label htmlFor="apiPayload" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>请求报文 (JSON)</span>
          <FileJson size={16} />
        </label>
        <textarea
          id="apiPayload"
          className="input-field"
          value={payload}
          onChange={(e) => setPayload(e.target.value)}
          style={{ fontFamily: 'var(--font-mono)', height: '240px' }}
          placeholder='{ "custNo": "00000194476241", "amount": 5000.0 }'
        />
      </div>
    </motion.div>
  );
}
